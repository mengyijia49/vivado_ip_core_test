from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from vivado_ip_test.plugins.floating_point.reciprocal_sqrt.reference import calculate, expected_transactions
from vivado_ip_test.plugins.floating_point.reciprocal_sqrt.spec import describe
from vivado_ip_test.plugins.floating_point.reciprocal_sqrt.vectors import directed_values, prepare_frames
from vivado_ip_test.plugins.floating_point.accuracy import reciprocal_tolerances
from unit.plugins.cycle_helpers import ROOT, plugin_case


def parameters(**changes):
    return {'operation': 'Reciprocal_square_root', 'input_exponent': 8, 'input_fraction': 24,
        'output_exponent': 8, 'output_fraction': 24, 'optimization': 'Resources',
        'has_last': False, 'user_width': 0, 'has_underflow': False,
        'has_overflow': False, 'has_invalid_op': True, 'has_divide_by_zero': True, **changes}


def exact_value(bits, fmt):
    _, exponent, fraction = fmt.unpack(bits)
    return Fraction((1 << fmt.fraction_bits) | fraction) * Fraction(2) ** (
        exponent - fmt.bias - fmt.fraction_bits)


def assert_rounded(test, source_bits, result_bits, source, target):
    x = exact_value(source_bits, source)
    _, exponent, fraction = target.unpack(result_bits)
    test.assertTrue(0 < exponent < target.exponent_mask)
    value = exact_value(result_bits, target)
    if result_bits > target.pack(0, 1, 0):
        lower = exact_value(result_bits - 1, target)
        midpoint = (lower + value) / 2
        comparison = Fraction(1, 1) - x * midpoint * midpoint
        test.assertTrue(comparison > 0 or (comparison == 0 and result_bits % 2 == 0))
    if fraction != target.fraction_mask or exponent != target.exponent_mask - 1:
        upper = exact_value(result_bits + 1, target)
        midpoint = (value + upper) / 2
        comparison = Fraction(1, 1) - x * midpoint * midpoint
        test.assertTrue(comparison < 0 or (comparison == 0 and result_bits % 2 == 0))


class ReciprocalSquareRootTests(unittest.TestCase):
    def test_small_format_exhaustive_against_fraction_midpoints(self):
        source = target = FloatFormat(4, 4)
        for bits in range(1 << source.width):
            sign, exponent, _ = source.unpack(bits)
            if sign or not 0 < exponent < source.exponent_mask:
                continue
            result, flags = calculate(bits, source, target)
            self.assertEqual(flags, {'invalid_op': False, 'divide_by_zero': False})
            assert_rounded(self, bits, result, source, target)

    def test_native_and_mixed_formats_satisfy_exact_rounding_intervals(self):
        rng = random.Random(20261131)
        formats = (FloatFormat(5, 11), FloatFormat(8, 24), FloatFormat(11, 53))
        for source in formats:
            for target in formats:
                checked = 0
                for _ in range(2000):
                    bits = rng.getrandbits(source.width - 1)
                    _, exponent, _ = source.unpack(bits)
                    if not 0 < exponent < source.exponent_mask:
                        continue
                    result, _ = calculate(bits, source, target)
                    _, output_exponent, _ = target.unpack(result)
                    if not 0 < output_exponent < target.exponent_mask:
                        continue
                    assert_rounded(self, bits, result, source, target)
                    checked += 1
                self.assertGreater(checked, 40)

    def test_special_values_flags_and_sidebands(self):
        fmt = FloatFormat(8, 24)
        for bits, wanted, flag in (
            (0, 0x7f800000, 'divide_by_zero'),
            (0x80000000, 0xff800000, 'divide_by_zero'),
            (1, 0x7f800000, 'divide_by_zero'),
            (0x3f800000, 0x3f800000, None),
            (0x40800000, 0x3f000000, None),
            (0x7f800000, 0, None),
            (0xff800000, 0x7fc00000, 'invalid_op'),
            (0xbf800000, 0x7fc00000, 'invalid_op'),
            (0x7f800001, 0x7fc00000, None)):
            value, flags = calculate(bits, fmt, fmt)
            self.assertEqual(value, wanted)
            self.assertEqual([name for name, active in flags.items() if active],
                             [] if flag is None else [flag])

        p = parameters(has_last=True, user_width=3)
        result = expected_transactions([{'tdata': 0, 'tlast': 1, 'tuser': 5}], p)[0]
        self.assertEqual(result, {'tdata': 0x7f800000, 'tlast': 1, 'tuser': 22})
        p['has_invalid_op'] = False
        self.assertEqual(expected_transactions([{'tdata': 0, 'tlast': 0, 'tuser': 5}], p)[0]['tuser'], 11)

    def test_spec_uses_catalog_operation_ports_and_native_formats(self):
        spec = describe(parameters(has_last=True, user_width=7))
        self.assertEqual(spec.input_prefix, 's_axis_a')
        self.assertEqual(spec.output_prefix, 'm_axis_result')
        self.assertEqual(spec.model_parameters['C_HAS_RECIP_SQRT'], 1)
        self.assertEqual(spec.model_parameters['C_HAS_RECIP'], 0)
        self.assertEqual(spec.model_parameters['C_A_TDATA_WIDTH'], 32)
        self.assertEqual(spec.model_parameters['C_RESULT_TDATA_WIDTH'], 32)
        self.assertEqual(spec.model_parameters['C_RESULT_TUSER_WIDTH'], 9)
        self.assertEqual(spec.settings['Operation_Type'], 'Rec_Square_Root')
        self.assertEqual(spec.settings['A_Precision_Type'], 'Single')
        self.assertEqual(spec.settings['Result_Precision_Type'], 'Single')
        for changes in ({'input_exponent': 6}, {'input_fraction': 11},
                        {'output_exponent': 8, 'output_fraction': 11},
                        {'output_exponent': 11, 'output_fraction': 53},
                        {'has_underflow': True}, {'has_overflow': True},
                        {'has_invalid_op': 1}, {'user_width': 257},
                        {'cycles_per_operation': 2}, {'architecture': 'Low_Latency'}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                describe(parameters(**changes))

    def test_directed_inputs_cover_rounding_specials_padding_and_signs(self):
        p = parameters(input_exponent=5, input_fraction=11,
                       output_exponent=5, output_fraction=11,
                       has_last=True, user_width=3)
        values = directed_values(p)
        self.assertTrue({0, 1, 0x3c00, 0x7bff, 0x7c00, 0x7e00,
                         0x8000, 0xbc00, 0xfc00} <= set(values))
        rows = prepare_frames([], describe(p), p)
        self.assertEqual({row['tdata'] >> 16 for row in rows}, {0})
        self.assertEqual({row['tlast'] for row in rows}, {0, 1})
        self.assertEqual({row['tuser'] for row in rows}, set(range(8)))
        self.assertGreater(len(values), 150)

    def test_accuracy_tolerance_is_limited_to_normal_single_double_results(self):
        p = parameters()
        frames = [{'tdata': value} for value in (0, 0x3f800001, 0x7f800000, 0xbf800000)]
        expected = expected_transactions(frames, p)
        tolerances = list(reciprocal_tolerances(frames, expected, p))
        self.assertEqual([row['tdata'] for row in tolerances], [0, 1, 0, 0])
        half = parameters(input_exponent=5, input_fraction=11,
                          output_exponent=5, output_fraction=11)
        self.assertEqual(list(reciprocal_tolerances(
            [{'tdata': 0x3c01}], expected_transactions([{'tdata': 0x3c01}], half), half))[0]['tdata'], 0)

    def test_generation_schema_and_96_matrix_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, base = plugin_case('floating_point', Path(directory))
            case = replace(base, case_id='reciprocal_sqrt_fixture', parameters=parameters(),
                verification=replace(base.verification, strategy='directed_random', case_budget=2048,
                                     coverage_targets=('port_boundaries',)))
            xci = Path(directory) / 'fake.xci'
            xci.write_text('{}')
            with patch('vivado_ip_test.plugins.common.stream.testbench.load_metadata',
                       return_value=(xci, {})):
                artifacts = plugin.generate_testbench(case)
            self.assertEqual(artifacts.metrics['reference_contract']['arithmetic'],
                             'exact_squared_midpoint')
            self.assertEqual(artifacts.metrics['comparison_kind'],
                             'accepted_axis_payload_bounded_distance')
            manifest = json.loads(artifacts.manifest_path.read_text())
            self.assertIn('output_tolerance', manifest['artifact_sha256'])
            self.assertEqual(manifest['output_layout']['fields'][0], {'name': 'tdata', 'width': 32})
            self.assertIn('s_axis_a_tdata', artifacts.testbench_path.read_text())

        schema = json.loads((ROOT / 'configs/schemas/ip/floating_point/reciprocal_sqrt.schema.json').read_text())
        self.assertEqual(set(schema['required']), set(parameters()))
        cases = load_test_cases(ROOT / 'configs/ip/floating_point/matrices/reciprocal_sqrt.json')
        self.assertEqual(len(cases), 96)
        self.assertEqual(len({tuple(sorted(case.parameters.items())) for case in cases}), 96)
        self.assertEqual(len({(case.parameters['input_exponent'], case.parameters['output_exponent'])
                              for case in cases}), 3)
        for case in cases:
            describe(case.parameters)


if __name__ == '__main__':
    unittest.main()

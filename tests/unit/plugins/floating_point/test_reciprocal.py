from dataclasses import replace
from fractions import Fraction
import json
import math
from pathlib import Path
import random
import struct
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from vivado_ip_test.plugins.floating_point.reciprocal.reference import calculate, expected_transactions
from vivado_ip_test.plugins.floating_point.reciprocal.spec import describe
from vivado_ip_test.plugins.floating_point.reciprocal.vectors import directed_values, prepare_frames
from unit.plugins.cycle_helpers import ROOT, plugin_case


def parameters(**changes):
    return {'operation': 'Reciprocal', 'input_exponent': 8, 'input_fraction': 24,
        'output_exponent': 8, 'output_fraction': 24, 'optimization': 'Resources',
        'has_last': False, 'user_width': 0, 'has_underflow': True,
        'has_overflow': False, 'has_invalid_op': False, 'has_divide_by_zero': True, **changes}


def exact_value(bits, fmt):
    sign, exponent, fraction = fmt.unpack(bits)
    magnitude = Fraction((1 << fmt.fraction_bits) | fraction) * Fraction(2) ** (
        exponent - fmt.bias - fmt.fraction_bits)
    return -magnitude if sign else magnitude


class ReciprocalTests(unittest.TestCase):
    def test_small_normals_match_independent_fraction_grid(self):
        source = target = FloatFormat(4, 4)
        grid = [(abs(exact_value(bits, target)), bits)
                for bits in range(256)
                if target.unpack(bits)[0] == 0 and 0 < target.unpack(bits)[1] < target.exponent_mask]
        for bits in range(256):
            sign, exponent, _ = source.unpack(bits)
            if not 0 < exponent < source.exponent_mask:
                continue
            exact = abs(1 / exact_value(bits, source))
            if not grid[0][0] <= exact <= grid[-1][0]:
                continue
            _, wanted = min(grid, key=lambda row: (abs(row[0] - exact), row[1] & 1))
            wanted |= sign << (target.width - 1)
            self.assertEqual(calculate(bits, source, target),
                             (wanted, {'underflow': False, 'divide_by_zero': False}))

    def test_native_and_mixed_formats_match_host_rounding(self):
        rng = random.Random(20261111)
        formats = ((5, 11, 'e'), (8, 24, 'f'), (11, 53, 'd'))
        for se, sp, source_code in formats:
            source = FloatFormat(se, sp)
            for te, tp, target_code in formats:
                target = FloatFormat(te, tp)
                checked = 0
                for _ in range(1000):
                    bits = rng.getrandbits(source.width)
                    _, exponent, _ = source.unpack(bits)
                    if not 0 < exponent < source.exponent_mask:
                        continue
                    value = struct.unpack('>' + source_code,
                                          bits.to_bytes(source.width // 8, 'big'))[0]
                    reciprocal = 1.0 / value
                    try:
                        encoded = struct.pack('>' + target_code, reciprocal)
                    except OverflowError:
                        encoded = struct.pack('>' + target_code,
                                              math.copysign(math.inf, reciprocal))
                    wanted = int.from_bytes(encoded, 'big')
                    _, output_exponent, _ = target.unpack(wanted)
                    if output_exponent == 0 and wanted & ((1 << (target.width - 1)) - 1):
                        continue
                    actual, _ = calculate(bits, source, target)
                    self.assertEqual(actual, wanted, (se, sp, te, tp, bits))
                    checked += 1
                self.assertGreater(checked, 800)

    def test_special_values_range_edges_and_flags(self):
        fmt = FloatFormat(8, 24)
        for bits, wanted, flag in (
            (0, 0x7f800000, 'divide_by_zero'),
            (0x80000000, 0xff800000, 'divide_by_zero'),
            (1, 0x7f800000, 'divide_by_zero'),
            (0x7f800000, 0, None),
            (0xff800000, 0x80000000, None),
            (0x7f800001, 0x7fc00000, None),
            (0x40400000, 0x3eaaaaab, None),
            (0x00800000, 0x7e800000, None),
            (0x7f7fffff, 0, 'underflow')):
            value, flags = calculate(bits, fmt, fmt)
            self.assertEqual(value, wanted)
            self.assertEqual([name for name, active in flags.items() if active],
                             [] if flag is None else [flag])

        self.assertEqual(calculate(0x00fffffe, fmt, fmt)[0], 0x7e000001)
        self.assertEqual(calculate(0x00ffffff, fmt, fmt)[0], 0x7e000001)
        double = FloatFormat(11, 53)
        self.assertEqual(calculate(0x001ffffffffffffe, double, double)[0], 0x7fc0000000000001)
        self.assertEqual(calculate(0x001fffffffffffff, double, double)[0], 0x7fc0000000000001)

    def test_cross_format_overflow_underflow_and_sidebands(self):
        source, half, double = FloatFormat(8, 24), FloatFormat(5, 11), FloatFormat(11, 53)
        self.assertEqual(calculate(0x00800000, source, half)[0], half.infinity(0))
        value, flags = calculate(0x7f7fffff, source, half)
        self.assertEqual(value, 0)
        self.assertTrue(flags['underflow'])
        self.assertEqual(calculate(0x3f800000, source, double)[0], double.pack(0, double.bias, 0))

        p = parameters(output_exponent=5, output_fraction=11, has_last=True, user_width=3)
        result = expected_transactions([{'tdata': 0, 'tlast': 1, 'tuser': 5}], p)[0]
        self.assertEqual(result, {'tdata': 0x7c00, 'tlast': 1, 'tuser': 22})
        p['has_underflow'] = False
        self.assertEqual(expected_transactions([{'tdata': 0, 'tlast': 0, 'tuser': 5}], p)[0]['tuser'], 11)

    def test_spec_uses_exact_catalog_ports_and_rejects_coercion(self):
        spec = describe(parameters(has_last=True, user_width=7))
        self.assertEqual(spec.input_prefix, 's_axis_a')
        self.assertEqual(spec.output_prefix, 'm_axis_result')
        self.assertEqual(spec.model_parameters['C_HAS_RECIP'], 1)
        self.assertEqual(spec.model_parameters['C_HAS_B'], 0)
        self.assertEqual(spec.model_parameters['C_A_TDATA_WIDTH'], 32)
        self.assertEqual(spec.model_parameters['C_RESULT_TDATA_WIDTH'], 32)
        self.assertEqual(spec.model_parameters['C_RESULT_TUSER_WIDTH'], 9)
        self.assertEqual(spec.settings['A_Precision_Type'], 'Single')
        self.assertEqual(spec.settings['Result_Precision_Type'], 'Single')
        self.assertEqual(spec.settings['C_Optimization'], 'Speed_Optimized')
        for changes in ({'input_exponent': 6}, {'input_fraction': 11},
                        {'output_exponent': 8, 'output_fraction': 11},
                        {'output_exponent': 5, 'output_fraction': 11},
                        {'has_overflow': True}, {'has_invalid_op': True},
                        {'has_underflow': 1}, {'user_width': 257},
                        {'cycles_per_operation': 2}, {'architecture': 'Low_Latency'}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                describe(parameters(**changes))

    def test_directed_inputs_cover_padding_specials_and_format_boundaries(self):
        p = parameters(input_exponent=5, input_fraction=11,
                       output_exponent=5, output_fraction=11,
                       has_last=True, user_width=3)
        values = directed_values(p)
        self.assertTrue({0, 1, 0x3c00, 0x7bff, 0x7c00, 0x7e00, 0x8000} <= set(values))
        rows = prepare_frames([], describe(p), p)
        self.assertEqual({row['tdata'] >> 16 for row in rows}, {0})
        self.assertEqual({row['tlast'] for row in rows}, {0, 1})
        self.assertEqual({row['tuser'] for row in rows}, set(range(8)))

    def test_generation_schema_and_96_matrix_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, base = plugin_case('floating_point', Path(directory))
            case = replace(base, case_id='reciprocal_fixture', parameters=parameters(),
                verification=replace(base.verification, strategy='directed_random', case_budget=1024,
                                     coverage_targets=('port_boundaries',)))
            xci = Path(directory) / 'fake.xci'
            xci.write_text('{}')
            with patch('vivado_ip_test.plugins.common.stream.testbench.load_metadata',
                       return_value=(xci, {})):
                artifacts = plugin.generate_testbench(case)
            self.assertEqual(artifacts.metrics['reference_contract']['arithmetic'], 'exact_integer_ratio')
            self.assertEqual(artifacts.metrics['comparison_kind'],
                             'accepted_axis_payload_bounded_distance')
            manifest = json.loads(artifacts.manifest_path.read_text())
            self.assertIn('output_tolerance', manifest['artifact_sha256'])
            self.assertEqual(manifest['output_layout']['fields'][0], {'name': 'tdata', 'width': 32})
            self.assertIn('s_axis_a_tdata', artifacts.testbench_path.read_text())

        schema = json.loads((ROOT / 'configs/schemas/ip/floating_point/reciprocal.schema.json').read_text())
        self.assertEqual(set(schema['required']), set(parameters()))
        cases = load_test_cases(ROOT / 'configs/ip/floating_point/matrices/reciprocal.json')
        self.assertEqual(len(cases), 96)
        self.assertEqual(len({tuple(sorted(case.parameters.items())) for case in cases}), 96)
        for case in cases:
            describe(case.parameters)


if __name__ == '__main__':
    unittest.main()

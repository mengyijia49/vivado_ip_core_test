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
from vivado_ip_test.plugins.floating_point.compare.reference import COMPARISONS, OPERATION_CODES, compare, expected_transactions
from vivado_ip_test.plugins.floating_point.compare.vectors import directed_pairs, prepare_frames, independent_gaps
from vivado_ip_test.services.stimulus_schedule import build_schedule
from unit.plugins.cycle_helpers import ROOT, plugin_case


def parameters(operation='Condition_Code', **changes):
    return {'operation': 'Compare', 'compare_operation': operation, 'input_exponent': 4, 'input_fraction': 4,
            'optimization': 'Resources', 'a_user_width': 0, 'b_user_width': 0, 'operation_user_width': 0,
            'has_a_last': False, 'has_b_last': False, 'has_operation_last': False, 'last_mode': 'None', **changes}


def fraction_value(bits, fmt):
    sign, exponent, fraction = fmt.unpack(bits)
    if exponent == fmt.exponent_mask:
        return float('nan') if fraction else float('-inf') if sign else float('inf')
    if not exponent:
        return Fraction(0)
    return (-1 if sign else 1) * Fraction((1 << fmt.fraction_bits) + fraction) * Fraction(2) ** (
        exponent - fmt.bias - fmt.fraction_bits)


class CompareTests(unittest.TestCase):
    def test_public_schema_keeps_comparison_and_unary_parameters_separate(self):
        directory = ROOT / 'configs/schemas/ip/floating_point'
        schema = json.loads((directory / 'parameters.schema.json').read_text())
        self.assertEqual(schema['oneOf'], [{'$ref': 'unary.schema.json'}, {'$ref': 'compare.schema.json'},
                                         {'$ref': 'arithmetic.schema.json'}, {'$ref': 'divide.schema.json'},
                                         {'$ref': 'fma.schema.json'}, {'$ref': 'reciprocal.schema.json'},
                                         {'$ref': 'reciprocal_sqrt.schema.json'},
                                         {'$ref': 'exponential.schema.json'},
                                         {'$ref': 'logarithm.schema.json'}])
        comparison = json.loads((directory / 'compare.schema.json').read_text())
        unary = json.loads((directory / 'unary.schema.json').read_text())
        self.assertEqual(set(comparison['required']), set(parameters()))
        self.assertFalse(comparison['additionalProperties'])
        self.assertNotIn('output_fraction', comparison['properties'])
        self.assertNotIn('compare_operation', unary['properties'])

    def test_all_small_input_pairs_and_modes_against_fraction_comparisons(self):
        fmt = FloatFormat(4, 4)
        values = [fraction_value(bits, fmt) for bits in range(256)]
        for a, av in enumerate(values):
            for b, bv in enumerate(values):
                unordered = av != av or bv != bv
                truths = (unordered, av < bv, av == bv, av <= bv, av > bv, av != bv, av >= bv)
                for mode, expected in zip(COMPARISONS[:7], truths):
                    self.assertEqual(compare(a, b, fmt, mode), int(expected), (a, b, mode))
                condition = 8 if unordered else 1 if av == bv else 2 if av < bv else 4
                self.assertEqual(compare(a, b, fmt, 'Condition_Code'), condition)

    def test_wide_formats_and_both_input_padding_fields(self):
        rng = random.Random(76)
        for exponent, precision in ((4, 5), (8, 24), (11, 53), (16, 64)):
            fmt = FloatFormat(exponent, precision)
            for _ in range(300):
                a, b = rng.getrandbits(fmt.width), rng.getrandbits(fmt.width)
                av, bv = fraction_value(a, fmt), fraction_value(b, fmt)
                expected = 8 if av != av or bv != bv else 1 if av == bv else 2 if av < bv else 4
                self.assertEqual(compare(a, b, fmt, 'Condition_Code'), expected)
                self.assertEqual(compare(a | (255 << fmt.width), b | (127 << fmt.width), fmt, 'Condition_Code'), expected)

    def test_programmable_codes_padding_and_reserved_code_rejection(self):
        fmt = FloatFormat(4, 4)
        for code, mode in OPERATION_CODES.items():
            for padding in range(4):
                for a, b in ((0, 0x80), (0x38, 0x40), (0x79, 0x38), (0xf8, 0x78)):
                    self.assertEqual(compare(a, b, fmt, 'Programmable', code | (padding << 6)), compare(a, b, fmt, mode))
        for code in (0, 3, 60, 63, 255):
            with self.assertRaises(ValueError):
                compare(0, 0, fmt, 'Programmable', code)

    def test_zero_padded_output_user_concatenation_and_last_modes(self):
        frame = {'a_tdata': 0x38, 'b_tdata': 0x40, 'operation_tdata': 12,
                 'a_tuser': 5, 'b_tuser': 17, 'operation_tuser': 2,
                 'a_tlast': 0, 'b_tlast': 1, 'operation_tlast': 1}
        p = parameters('Programmable', a_user_width=3, b_user_width=5, operation_user_width=2,
                       has_a_last=True, has_b_last=True, has_operation_last=True)
        for mode, last in (('A', 0), ('B', 1), ('Operation', 1), ('Or', 1), ('And', 0)):
            self.assertEqual(expected_transactions([frame], {**p, 'last_mode': mode}),
                             [{'tdata': 1, 'tuser': 653, 'tlast': last}])
        self.assertEqual(frame['a_tdata'], 0x38)

    def test_parameter_constraints_and_metadata_shapes(self):
        plugin, _ = plugin_case('floating_point')
        spec = plugin.describe(parameters('Programmable', a_user_width=256, b_user_width=256, operation_user_width=256))
        self.assertEqual(spec.input_lane_count, 3)
        self.assertEqual(spec.sink_payload[-1].width, 768)
        self.assertEqual(spec.model_parameters['C_COMPARE_OPERATION'], 8)
        self.assertEqual(spec.model_parameters['C_RESULT_WIDTH'], 1)
        self.assertEqual(plugin.describe(parameters()).model_parameters['C_RESULT_WIDTH'], 4)
        for changes in ({'compare_operation': 'Unknown'}, {'input_exponent': True}, {'input_fraction': 65},
                        {'a_user_width': 257}, {'has_a_last': 1}, {'operation_user_width': 1},
                        {'has_operation_last': True}, {'last_mode': 'Or'},
                        {'has_a_last': True}, {'last_mode': 'B', 'has_a_last': True},
                        {'input_exponent': 4, 'input_fraction': 64}, {'cycles_per_operation': 2},
                        {'has_invalid_op': True}, {'output_exponent': 1}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                plugin.describe(parameters(**changes))

    def test_each_numeric_pair_gets_every_programmable_operation(self):
        plugin, _ = plugin_case('floating_point')
        p = parameters('Programmable', has_a_last=True, has_b_last=True, has_operation_last=True,
                       last_mode='Or', a_user_width=1, b_user_width=3, operation_user_width=2)
        spec = plugin.describe(p)
        frames = [{'a_tdata': 0x38, 'b_tdata': 0x40, 'a_tuser': 1, 'b_tuser': 3, 'operation_tuser': 2}]
        original = [dict(f) for f in frames]
        prepared = prepare_frames(frames, spec, p)
        self.assertEqual(frames, original)
        self.assertEqual({f['operation_tdata'] & 63 for f in prepared[-7:]}, set(OPERATION_CODES))
        self.assertEqual({f['operation_tdata'] >> 6 for f in prepared}, set(range(4)))
        self.assertEqual({(f['a_tlast'], f['b_tlast'], f['operation_tlast']) for f in prepared},
                         {(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)})
        self.assertTrue(all(set(f) == {port.name for port in spec.payload} for f in prepared))
        for lane, width in (('a', 1), ('b', 3), ('operation', 2)):
            self.assertEqual({f[lane + '_tuser'] for f in prepared}, set(range(1 << width)))
        self.assertIn((0, 0x80), directed_pairs(FloatFormat(4, 4)))
        self.assertIn((0x38, 0x39), directed_pairs(FloatFormat(4, 4)))

    def test_generation_has_independent_cursors_and_reproducible_timing(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, _ = plugin_case('floating_point', Path(directory))
            case = next(c for c in load_test_cases(ROOT / 'configs/ip/floating_point/regression/compare.json')
                        if c.case_id == 'fp_compare16_programmable_and')
            xci = Path(directory) / 'fixture.xci'
            xci.write_text('{}')
            with patch('vivado_ip_test.plugins.common.stream.testbench.load_metadata', return_value=(xci, {})):
                first = plugin.generate_testbench(case)
                contents = first.input_path.read_bytes()
                second = plugin.generate_testbench(case)
            self.assertEqual(contents, second.input_path.read_bytes())
            text = first.testbench_path.read_text()
            self.assertIn('acknowledged(b) + 1', text)
            self.assertIn('accepted_rows(acknowledged(b))', text)
            self.assertNotIn('(and acknowledged)', text)
            self.assertIn('max_accepted_operand_skew=', text)
            self.assertIn('source wiring mismatch', text)
            self.assertEqual(first.metrics['input_lane_count'], 3)
            self.assertEqual(first.metrics['checked_input_transfers'], 3 * first.vector_count)
            manifest = json.loads(first.manifest_path.read_text())
            schedule = json.loads(Path(manifest['artifacts']['schedule']).read_text())
            self.assertTrue(any(len(set(row)) > 1 for row in schedule['gaps_by_lane']))
            self.assertEqual(first.metrics['reference_contract']['input_barrier'], False)
            timing = build_schedule(100, case.verification, can_idle=True)
            a = independent_gaps(timing, case.verification, 3)
            self.assertEqual(a, independent_gaps(timing, case.verification, 3))
            self.assertNotEqual(a, independent_gaps(timing, replace(case.verification, random_seed=2), 3))
            self.assertEqual(independent_gaps(timing, replace(case.verification, timing_mode='continuous'), 3), [[0]*3]*100)

from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.floating_point.arithmetic.reference import calculate as arithmetic
from vivado_ip_test.plugins.floating_point.fma.reference import calculate, expected_transactions
from vivado_ip_test.plugins.floating_point.fma.spec import describe
from vivado_ip_test.plugins.floating_point.fma.vectors import directed_triples, prepare_frames
from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from unit.plugins.cycle_helpers import ROOT, plugin_case


def parameters(**changes):
    return {'operation': 'FMA', 'input_exponent': 8, 'input_fraction': 24,
        'optimization': 'Resources', 'mult_usage': 'Medium_Usage',
        'a_user_width': 0, 'b_user_width': 0, 'c_user_width': 0, 'operation_user_width': 0,
        'has_a_last': False, 'has_b_last': False, 'has_c_last': False,
        'has_operation_last': False, 'last_mode': 'None',
        'has_underflow': True, 'has_overflow': True, 'has_invalid_op': True, **changes}


def small_fraction(bits):
    sign, exponent, fraction = (bits >> 7) & 1, (bits >> 3) & 15, bits & 7
    if exponent == 0:
        return Fraction(0)
    value = Fraction(8 + fraction, 8) * Fraction(2) ** (exponent - 7)
    return -value if sign else value


class FmaTests(unittest.TestCase):
    def test_fused_residue_differs_from_separate_multiply_and_add(self):
        for e, precision in ((5, 11), (8, 24), (11, 53)):
            fmt = FloatFormat(e, precision)
            one = fmt.pack(0, fmt.bias, 0)
            k = min(fmt.fraction_bits, max(2, (fmt.bias - 2) // 2))
            a = one + (1 << (fmt.fraction_bits - k))
            b = one - (1 << (fmt.precision - k))
            fused, flags = calculate(a, b, one | (1 << (fmt.width - 1)), fmt)
            product, _ = arithmetic(a, b, fmt, 'Multiply')
            separate, _ = arithmetic(product, one | (1 << (fmt.width - 1)), fmt, 'Add')
            self.assertNotEqual(fused, separate)
            self.assertEqual(separate & ((1 << (fmt.width - 1)) - 1), 0)
            self.assertEqual(flags, {'underflow': False, 'overflow': False, 'invalid_op': False})

    def test_small_finite_values_match_fraction_grid(self):
        fmt = FloatFormat(4, 4)
        grid = []
        for sign in (0, 1):
            for exponent in range(1, 15):
                for fraction in range(8):
                    bits = (sign << 7) | (exponent << 3) | fraction
                    grid.append((small_fraction(bits), bits))
        rng = random.Random(20261101)
        normals = [bits for _, bits in grid]
        for _ in range(10000):
            a, b, c = (rng.choice(normals) for _ in range(3))
            exact = small_fraction(a) * small_fraction(b) + small_fraction(c)
            if not Fraction(1, 64) <= abs(exact) <= Fraction(15, 2) or exact == 0:
                continue
            _, wanted = min(grid, key=lambda row: (abs(row[0] - exact), row[1] & 1))
            actual, flags = calculate(a, b, c, fmt)
            self.assertEqual((actual, flags), (wanted, {
                'underflow': False, 'overflow': False, 'invalid_op': False}))

    def test_nan_infinity_zero_and_zero_sign_rules(self):
        fmt = FloatFormat(8, 24)
        one, inf, ninf, qnan = 0x3f800000, 0x7f800000, 0xff800000, 0x7fc00000
        for values, expected, invalid in (
            ((inf, 0, one), qnan, True), ((0, ninf, one), qnan, True),
            ((inf, one, ninf), qnan, True), ((ninf, one, ninf), ninf, False),
            ((one, one, inf), inf, False), ((0x7f800001, one, inf), qnan, False),
            ((0x80000000, 0, 0x80000000), 0x80000000, False),
            ((0x80000000, 0, 0), 0, False)):
            value, flags = calculate(*values, fmt)
            self.assertEqual(value, expected)
            self.assertEqual(flags['invalid_op'], invalid)
        self.assertEqual(calculate(one, one, one, fmt, 0)[0], 0x40000000)
        self.assertEqual(calculate(one, one, one, fmt, 1)[0], 0)
        for code in (2, 17, 63, 255):
            with self.assertRaises(ValueError):
                calculate(one, one, one, fmt, code)

    def test_sideband_order_includes_c_between_b_and_exceptions(self):
        p = parameters(a_user_width=2, b_user_width=3, c_user_width=4,
                       has_a_last=True, has_b_last=True, has_c_last=True, last_mode='And')
        frame = {'a_tdata': 0x7f800000, 'b_tdata': 0, 'c_tdata': 0x3f800000,
                 'operation_tdata': 0,
                 'a_tuser': 2, 'b_tuser': 5, 'c_tuser': 9,
                 'a_tlast': 1, 'b_tlast': 0, 'c_tlast': 1}
        result = expected_transactions([frame], p)[0]
        self.assertEqual(result['tdata'], 0x7fc00000)
        self.assertEqual(result['tuser'], 1 << 2 | 2 << 3 | 5 << 5 | 9 << 8)
        self.assertEqual(result['tlast'], 0)

    def test_spec_ports_model_and_validation(self):
        spec = describe(parameters(c_user_width=7, has_c_last=True, last_mode='C'))
        self.assertEqual([lane for lane, _ in spec.lanes], ['a', 'b', 'c', 'operation'])
        self.assertEqual(spec.model_parameters['C_HAS_FMA'], 1)
        self.assertEqual(spec.model_parameters['C_HAS_FMS'], 1)
        self.assertEqual(spec.model_parameters['C_HAS_C'], 1)
        self.assertEqual(spec.model_parameters['C_C_TDATA_WIDTH'], 32)
        self.assertIn('s_axis_c_tdata', {port.name for port in spec.inputs})
        self.assertEqual(spec.settings['C_Optimization'], 'Speed_Optimized')
        for changes in ({'input_exponent': 6}, {'input_fraction': 23}, {'mult_usage': 'No_Usage'},
                        {'architecture': 'Low_Latency'}, {'last_mode': 'Operation'},
                        {'last_mode': 'C'}, {'has_invalid_op': 1}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                describe(parameters(**changes))

    def test_directed_vectors_cover_fused_special_padding_and_all_last_patterns(self):
        p = parameters(input_exponent=5, input_fraction=11, a_user_width=2, b_user_width=3,
                       c_user_width=4, operation_user_width=5,
                       has_a_last=True, has_b_last=True, has_c_last=True,
                       has_operation_last=True, last_mode='Or')
        spec = describe(p)
        triples = directed_triples(p)
        self.assertIn((0x7c00, 0, 0x3c00), triples)
        rows = prepare_frames([], spec, p)
        self.assertEqual({(r['a_tlast'], r['b_tlast'], r['c_tlast'], r['operation_tlast']) for r in rows},
                         {(a, b, c, op) for a in (0, 1) for b in (0, 1)
                          for c in (0, 1) for op in (0, 1)})
        self.assertEqual({row['operation_tdata'] for row in rows}, {0, 1, 64, 65, 128, 129, 192, 193})
        self.assertTrue(any(row['a_tuser'] for row in rows))

    def test_generation_and_all_matrix_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, base = plugin_case('floating_point', Path(directory))
            case = replace(base, case_id='fma_fixture', parameters=parameters(),
                           verification=replace(base.verification, strategy='directed_random', case_budget=1024,
                                                coverage_targets=('port_boundaries',)))
            xci = Path(directory) / 'fake.xci'
            xci.write_text('{}')
            with patch('vivado_ip_test.plugins.common.stream.testbench.load_metadata', return_value=(xci, {})):
                artifacts = plugin.generate_testbench(case)
            self.assertEqual(artifacts.metrics['input_lane_count'], 4)
            self.assertFalse(artifacts.metrics['reference_contract']['intermediate_rounding'])
            self.assertIn('s_axis_c_tvalid', artifacts.testbench_path.read_text())
            manifest = json.loads(artifacts.manifest_path.read_text())
            self.assertEqual(manifest['output_layout']['fields'][0], {'name': 'tdata', 'width': 32})

        from vivado_ip_test.configuration import load_test_cases
        cases = load_test_cases(ROOT / 'configs/ip/floating_point/matrices/fma.json')
        self.assertEqual(len(cases), 96)
        for case in cases:
            describe(case.parameters)

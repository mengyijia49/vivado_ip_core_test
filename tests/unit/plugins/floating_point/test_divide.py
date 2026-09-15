from bisect import bisect_left
from dataclasses import replace
from fractions import Fraction
import json
import math
from pathlib import Path
import random
import re
import struct
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.floating_point.divide.reference import calculate, expected_transactions
from vivado_ip_test.plugins.floating_point.divide.spec import describe
from vivado_ip_test.plugins.floating_point.divide.vectors import midpoint_significands, directed_pairs, prepare_frames
from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from vivado_ip_test.plugins.floating_point.multi_input.testbench import render_testbench
from vivado_ip_test.plugins.floating_point.multi_input.vectors import USER_PATTERN, user_tag
from unit.plugins.cycle_helpers import ROOT, plugin_case
from unit.plugins.floating_point.test_arithmetic import small_values


def parameters(**changes):
    return {'operation': 'Divide', 'input_exponent': 4, 'input_fraction': 4,
        'cycles_per_operation': 1, 'optimization': 'Resources',
        'a_user_width': 0, 'b_user_width': 0, 'operation_user_width': 0,
        'has_a_last': False, 'has_b_last': False, 'has_operation_last': False, 'last_mode': 'None',
        'has_underflow': True, 'has_overflow': True, 'has_invalid_op': True, 'has_divide_by_zero': True,
        **changes}


class DivideTests(unittest.TestCase):
    def test_independent_probe_literals_match_numeric_contract(self):
        from integration.ip.floating_point.test_divide_failure_detection import INPUTS, RESULTS, FLAGS
        self.assertEqual(len(INPUTS), 16)
        self.assertEqual(len(INPUTS), len(RESULTS))
        self.assertEqual(len(INPUTS), len(FLAGS))
        for operands, expected, expected_flags in zip(INPUTS, RESULTS, FLAGS):
            value, flags = calculate(*operands, FloatFormat(8, 24))
            self.assertEqual(value, expected, operands)
            names = ('underflow', 'overflow', 'invalid_op', 'divide_by_zero')
            self.assertEqual(sum(int(flags[name]) << i for i, name in enumerate(names)), expected_flags)

    def test_all_small_pairs_against_exact_fraction_rounding_grid(self):
        values = small_values()
        grid = [(Fraction(m) * Fraction(2) ** (e - 3), m, e) for e in range(-24, 21) for m in range(8, 16)]
        ordered = [r[0] for r in grid]
        for a, av in enumerate(values):
            for b, bv in enumerate(values):
                sign = ((a ^ b) >> 7) & 1
                flags = {name: False for name in ('underflow', 'overflow', 'invalid_op', 'divide_by_zero')}
                if math.isnan(av) or math.isnan(bv):
                    expected = 0x7c
                elif av == bv == 0 or math.isinf(av) and math.isinf(bv):
                    expected = 0x7c
                    flags['invalid_op'] = True
                elif math.isinf(av):
                    expected = (sign << 7) | 0x78
                elif math.isinf(bv) or av == 0:
                    expected = sign << 7
                elif bv == 0:
                    expected = (sign << 7) | 0x78
                    flags['divide_by_zero'] = True
                else:
                    magnitude = abs(Fraction(av) / Fraction(bv))
                    i = bisect_left(ordered, magnitude)
                    _, mantissa, exponent = min(grid[max(0, i - 1):i + 1],
                        key=lambda r: (abs(r[0] - magnitude), r[1] % 2))
                    flags['underflow'], flags['overflow'] = exponent < -6, exponent > 7
                    expected = sign << 7
                    if flags['overflow']:
                        expected |= 0x78
                    elif not flags['underflow']:
                        expected |= ((exponent + 7) << 3) | (mantissa - 8)
                self.assertEqual(calculate(a, b, FloatFormat(4, 4)), (expected, flags), (a, b))

    def test_native_formats_against_host_division(self):
        rng = random.Random(9197)
        for e, precision, code in ((5, 11, 'e'), (8, 24, 'f'), (11, 53, 'd')):
            fmt = FloatFormat(e, precision)
            checked = 0
            for _ in range(1000):
                a, b = rng.getrandbits(fmt.width), rng.getrandbits(fmt.width)
                av, bv = (struct.unpack('>' + code, bits.to_bytes(fmt.width // 8, 'big'))[0] for bits in (a, b))
                if any(not math.isfinite(v) for v in (av, bv)) or any(fmt.unpack(bits)[1] == 0 for bits in (a, b)):
                    continue
                value = av / bv
                if 0 < abs(value) < math.ldexp(1.0, 1 - fmt.bias):
                    continue
                try:
                    packed = struct.pack('>' + code, value)
                except OverflowError:
                    packed = struct.pack('>' + code, math.copysign(math.inf, value))
                self.assertEqual(calculate(a, b, fmt)[0], int.from_bytes(packed, 'big'), (e, precision, a, b))
                checked += 1
            self.assertGreater(checked, 400)

    def test_special_values_keep_divide_by_zero_separate_from_invalid(self):
        for a, b, expected, flag in (
            (0x38, 0, 0x78, 'divide_by_zero'), (0xb8, 0, 0xf8, 'divide_by_zero'),
            (0x38, 0x80, 0xf8, 'divide_by_zero'), (0xb8, 0x80, 0x78, 'divide_by_zero'),
            (0x38, 1, 0x78, 'divide_by_zero'), (1, 0x38, 0, None),
            (0, 0, 0x7c, 'invalid_op'), (1, 0x81, 0x7c, 'invalid_op'),
            (0x78, 0xf8, 0x7c, 'invalid_op'), (0x78, 0, 0x78, None),
            (0x38, 0xf8, 0x80, None), (0x79, 0, 0x7c, None),
            (0x78, 0x79, 0x7c, None), (0x80, 0x38, 0x80, None)):
            result, flags = calculate(a, b, FloatFormat(4, 4))
            self.assertEqual(result, expected)
            self.assertEqual([key for key, value in flags.items() if value], [] if flag is None else [flag])

    def test_literals_cover_recurring_quotients_and_range_boundaries(self):
        for a, b, value, flag in (
            (0x3f800000, 0x40400000, 0x3eaaaaab, None),
            (0x3f800000, 0x40e00000, 0x3e124925, None),
            (0x00800000, 0x40000000, 0, 'underflow'),
            (0x80800000, 0x40000000, 0x80000000, 'underflow'),
            (0x7f7fffff, 0x3f000000, 0x7f800000, 'overflow'),
            (0xff7fffff, 0x3f000000, 0xff800000, 'overflow'),
            (0x00800000, 0x00800000, 0x3f800000, None),
            (0x7f7fffff, 0x7f7fffff, 0x3f800000, None)):
            result, flags = calculate(a, b, FloatFormat(8, 24))
            self.assertEqual(result, value)
            self.assertEqual([key for key, value in flags.items() if value], [] if flag is None else [flag])

    def test_wide_format_and_both_padding_fields(self):
        fmt = FloatFormat(16, 64)
        one, maximum, minimum = fmt.pack(0, fmt.bias, 0), fmt.infinity(0) - 1, fmt.pack(0, 1, 0)
        for value in (minimum, maximum, fmt.pack(1, fmt.bias, 123456789)):
            self.assertEqual(calculate(value, one, fmt)[0], value)
            self.assertEqual(calculate(value, value, fmt)[0], one)
        self.assertTrue(calculate(maximum, minimum, fmt)[1]['overflow'])
        self.assertTrue(calculate(minimum, maximum, fmt)[1]['underflow'])
        for pa in (0, 0xfe00):
            for pb in (0, 0xfe00):
                self.assertEqual(calculate(0x170 | pa, 0x070 | pb, FloatFormat(4, 5))[0], 0x170)
        p = parameters(input_fraction=5)
        self.assertEqual(expected_transactions([{'a_tdata':0x170,'b_tdata':0x070}],p)[0]['tdata'],0xff70)

    def test_all_exception_subsets_and_sideband_positions(self):
        names = ('underflow', 'overflow', 'invalid_op', 'divide_by_zero')
        frames = [(0x08, 0x40, 1), (0x77, 0x30, 2), (0, 0, 4), (0x38, 0, 8)]
        for mask in range(16):
            selected = [i for i in range(4) if mask & (1 << i)]
            p = parameters(a_user_width=3,b_user_width=5,has_a_last=True,has_b_last=True,last_mode='Or',
                           **{'has_'+name:bool(mask & (1<<i)) for i,name in enumerate(names)})
            for a,b,flag in frames:
                frame={'a_tdata':a,'b_tdata':b,'a_tuser':5,'b_tuser':17,'a_tlast':0,'b_tlast':1}
                result = expected_transactions([frame],p)[0]
                wanted = (141 << len(selected)) | sum(int(bool(flag & (1<<bit))) << j for j,bit in enumerate(selected))
                self.assertEqual(result['tuser'],wanted)
                self.assertEqual(result['tlast'],1)

    def test_rate_and_parameter_validation(self):
        for e,precision in ((4,4),(5,11),(8,24),(11,53),(16,64)):
            for rate in range(1,precision+3):
                spec=describe(parameters(input_exponent=e,input_fraction=precision,cycles_per_operation=rate))
                self.assertEqual(spec.transfer_interval_cycles,rate)
                self.assertEqual(spec.settings['C_Rate'],rate)
                self.assertEqual(spec.model_parameters['C_HAS_DIVIDE_BY_ZERO'],1)
        for changes in ({'cycles_per_operation':0},{'cycles_per_operation':7},{'cycles_per_operation':True},
                        {'cycles_per_operation':1.5},{'input_fraction':64},{'has_divide_by_zero':1},
                        {'input_exponent':True},{'operation_user_width':1},{'has_operation_last':True},
                        {'architecture':'Low_Latency'},{'mult_usage':'No_Usage'},
                        {'last_mode':'A'},{'a_user_width':257},{'output_fraction':4},{'add_sub_value':'Both'}):
            with self.subTest(changes=changes),self.assertRaises(PluginError):
                describe(parameters(**changes))

    def test_modular_midpoint_generation_reaches_both_sides(self):
        for precision in range(4,65):
            pairs=midpoint_significands(precision)
            sides=set()
            self.assertTrue(pairs)
            for numerator,denominator in pairs:
                shift=precision-1+int(numerator<denominator)
                remainder=(numerator<<shift)%denominator
                delta=2*remainder-denominator
                self.assertIn(delta,(-1,1))
                sides.add(delta)
            self.assertEqual(sides,{-1,1})
        p=parameters(input_exponent=8,input_fraction=24)
        pairs=set(directed_pairs(p))
        self.assertTrue({(0,0),(0x3f800000,0),(0x7f800000,0xff800000),
                         (0x00800000,0x40000000),(0x7f7fffff,0x3f000000)} <= pairs)

    def test_preparation_varies_padding_and_has_no_operation_channel(self):
        p=parameters(input_fraction=5,has_a_last=True,has_b_last=True,last_mode='And')
        frames=prepare_frames([],describe(p),p)
        self.assertEqual({(r['a_tdata']>>9,r['b_tdata']>>9) for r in frames},{(0,0),(0,127),(127,0),(127,127)})
        self.assertEqual({(r['a_tlast'],r['b_tlast']) for r in frames},{(0,0),(0,1),(1,0),(1,1)})
        self.assertTrue(all('operation_tdata' not in r for r in frames))

    def test_generation_and_watchdog_follow_rate_without_spacing_offered_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin,base=plugin_case('floating_point',Path(directory))
            case=replace(base,case_id='divide_fixture',parameters=parameters(cycles_per_operation=6),
                         verification=replace(base.verification,strategy='directed_random',case_budget=256,
                                              coverage_targets=('port_boundaries',)))
            xci=Path(directory)/'fake.xci'; xci.write_text('{}')
            with patch('vivado_ip_test.plugins.common.stream.testbench.load_metadata',return_value=(xci,{})):
                artifacts=plugin.generate_testbench(case)
            self.assertEqual(artifacts.metrics['input_lane_count'],2)
            contract=artifacts.metrics['reference_contract']
            self.assertFalse(contract['input_barrier'])
            self.assertEqual(contract['cycles_per_operation'],6)
            self.assertEqual(contract['user_pattern'], USER_PATTERN)
            manifest=json.loads(artifacts.manifest_path.read_text())
            self.assertEqual(manifest['output_layout']['fields'],[{'name':'tdata','width':8},{'name':'tuser','width':4}])
            paths={name:Path(value) for name,value in manifest['artifacts'].items()}
            fast=render_testbench(describe(parameters()),paths,artifacts.vector_count,8,240)
            slow=render_testbench(describe(parameters(cycles_per_operation=6)),paths,artifacts.vector_count,8,240)
            timeout=lambda text:int(re.findall(r'wait for (\d+) ns;',text)[-1])
            self.assertGreater(timeout(slow),timeout(fast))
            schema=json.loads((ROOT/'configs/schemas/ip/floating_point/divide.schema.json').read_text())
            self.assertEqual(set(schema['required']),set(parameters()))

    def test_user_patterns_keep_narrow_lanes_and_wide_high_bits_active(self):
        for width in (1, 2, 3, 5, 31, 32, 129, 256):
            limit = (1 << width) - 1
            for lane in (0, 1, 2):
                rows = [user_tag(i, lane, width) for i in range(8 * width)]
                self.assertTrue(all(0 <= value <= limit for value in rows))
                self.assertIn(0, rows)
                self.assertIn(limit, rows)
                self.assertTrue({1 << bit for bit in range(width)} <= set(rows))
                self.assertTrue({limit ^ (1 << bit) for bit in range(width)} <= set(rows))
        self.assertNotEqual(user_tag(4, 0, 256) >> 128, user_tag(4, 1, 256) >> 128)
        p = parameters(a_user_width=1, b_user_width=5)
        frames = prepare_frames([], describe(p), p)
        self.assertTrue({0, 31} <= {frame['b_tuser'] for frame in frames})
        self.assertTrue(any(frame['b_tuser'] & 1 for frame in frames))

    def test_shipped_divide_matrix_structure_and_common_membership(self):
        directory = ROOT / 'configs/ip/floating_point'
        common = json.loads((directory / 'regression/divide.json').read_text())['cases']
        total, found, formats = 0, set(), set()
        matrix = directory / 'matrices/divide.json'
        for name in json.loads(matrix.read_text())['includes']:
            index = matrix.parent / name
            for child in json.loads(index.read_text())['includes']:
                leaf = index.parent / child
                data = json.loads(leaf.read_text())
                self.assertTrue((leaf.parent / data['$schema']).resolve().is_file())
                count = 0
                for sweep in data['sweeps']:
                    p, axes = sweep['template']['parameters'], sweep['axes']
                    formats.add((p['input_exponent'], p['input_fraction']))
                    self.assertEqual(axes['cycles_per_operation'], list(range(1, p['input_fraction'] + 3)))
                    count += math.prod(len(values) for values in axes.values())
                    describe(p)
                    for i, case in enumerate(common):
                        row = case['parameters']
                        if all(row[key] in axes[key] if key in axes else row[key] == value for key, value in p.items()):
                            found.add(i)
                self.assertLessEqual(count, 10560)
                total += count
        self.assertEqual(len(formats), 645)
        self.assertEqual(total, 3578240)
        self.assertEqual(found, set(range(12)))

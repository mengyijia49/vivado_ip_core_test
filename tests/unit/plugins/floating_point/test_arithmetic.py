from bisect import bisect_left
from dataclasses import replace
import json
import math
from math import prod
from pathlib import Path
import random
import struct
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.floating_point.arithmetic.reference import calculate, expected_transactions
from vivado_ip_test.plugins.floating_point.arithmetic.spec import describe, implementation_options
from vivado_ip_test.plugins.floating_point.arithmetic.vectors import directed_pairs, prepare_frames
from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from unit.plugins.cycle_helpers import ROOT, plugin_case


def parameters(operation='Add_Subtract', **changes):
    return {'operation': operation, 'input_exponent': 4, 'input_fraction': 4,
        'optimization': 'Resources', 'architecture': 'Speed_Optimized', 'mult_usage': 'No_Usage',
        'a_user_width': 0, 'b_user_width': 0, 'operation_user_width': 0,
        'has_a_last': False, 'has_b_last': False, 'has_operation_last': False, 'last_mode': 'None',
        'has_underflow': True, 'has_overflow': True, 'has_invalid_op': True,
        **({'add_sub_value': 'Both'} if operation == 'Add_Subtract' else {}), **changes}


def small_values():
    values = []
    for bits in range(256):
        exponent, fraction = (bits >> 3) & 15, bits & 7
        magnitude = (math.nan if fraction else math.inf) if exponent == 15 else (
            math.ldexp(float(8 + fraction), exponent - 10) if exponent else 0.0)
        values.append(-magnitude if bits & 128 else magnitude)
    return values


class ArithmeticTests(unittest.TestCase):
    def test_literal_addition_probe_values_agree_without_being_generated_by_reference(self):
        from integration.ip.floating_point.test_arithmetic_failure_detection import INPUTS, RESULTS, FLAGS
        for (a, b, code), value, mask in zip(INPUTS, RESULTS, FLAGS):
            actual, flags = calculate(a, b, FloatFormat(4, 4), 'Both', code)
            packed_flags = sum(int(flags[name]) << i for i, name in enumerate(
                               ('underflow', 'overflow', 'invalid_op')))
            self.assertEqual((actual, packed_flags), (value, mask))

    def test_arithmetic_matrix_shapes_counts_and_common_parameter_membership(self):
        directory = ROOT / 'configs/ip/floating_point'

        def leaves(path):
            data = json.loads(path.read_text())
            self.assertTrue((path.parent / data['$schema']).resolve().is_file())
            if 'includes' in data:
                for child in data['includes']:
                    yield from leaves(path.parent / child)
            else:
                yield data['sweeps']

        for operation, name, expected_count in (('Add_Subtract', 'add_subtract', 407472),
                                                 ('Multiply', 'multiply', 402896)):
            common = [row['parameters'] for row in json.loads((directory / f'regression/{name}.json').read_text())['cases']]
            found = set()
            total = 0
            for sweeps in leaves(directory / f'matrices/{name}.json'):
                count = sum(prod(len(values) for values in sweep['axes'].values()) for sweep in sweeps)
                self.assertLessEqual(count, 20000)
                total += count
                for sweep in sweeps:
                    p, axes = sweep['template']['parameters'], sweep['axes']
                    self.assertEqual(p['operation'], operation)
                    for precision in axes['input_fraction']:
                        describe({**p, 'input_fraction': precision})
                    for i, row in enumerate(common):
                        if all(row[key] in axes[key] if key in axes else row[key] == value
                               for key, value in p.items()):
                            found.add(i)
            self.assertEqual(total, expected_count)
            self.assertEqual(found, set(range(len(common))))

    def test_all_small_pairs_against_an_independent_rounding_grid(self):
        values = small_values()
        grid = [(math.ldexp(float(m), e - 3), m, e) for e in range(-24, 21) for m in range(8, 16)]
        ordered = [r[0] for r in grid]
        fmt = FloatFormat(4, 4)
        for operation, evaluate in (('Add', lambda a, b: a + b), ('Subtract', lambda a, b: a - b),
                                    ('Multiply', lambda a, b: a * b)):
            for a, av in enumerate(values):
                for b, bv in enumerate(values):
                    value = evaluate(av, bv)
                    sign = int(math.copysign(1, value) < 0)
                    flags = {'underflow': False, 'overflow': False, 'invalid_op': False}
                    if math.isnan(value):
                        expected = 0x7c
                        flags['invalid_op'] = not (math.isnan(av) or math.isnan(bv))
                    elif math.isinf(value):
                        expected = (sign << 7) | 0x78
                    elif value == 0:
                        expected = sign << 7
                    else:
                        magnitude = abs(value)
                        i = bisect_left(ordered, magnitude)
                        _, mantissa, exponent = min(grid[max(0, i - 1):i + 1],
                                                   key=lambda r: (abs(r[0] - magnitude), r[1] % 2))
                        flags['underflow'], flags['overflow'] = exponent < -6, exponent > 7
                        expected = sign << 7
                        if flags['overflow']:
                            expected |= 0x78
                        elif not flags['underflow']:
                            expected |= ((exponent + 7) << 3) | (mantissa - 8)
                    self.assertEqual(calculate(a, b, fmt, operation), (expected, flags), (operation, a, b))

    def test_native_formats_against_host_arithmetic_away_from_underflow_boundary(self):
        rng = random.Random(492)
        for e, precision, code in ((5, 11, 'e'), (8, 24, 'f'), (11, 53, 'd')):
            fmt = FloatFormat(e, precision)
            length = fmt.width // 8
            for _ in range(500):
                a, b = rng.getrandbits(fmt.width), rng.getrandbits(fmt.width)
                av, bv = (struct.unpack('>' + code, bits.to_bytes(length, 'big'))[0] for bits in (a, b))
                if any(not math.isfinite(v) for v in (av, bv)) or any(fmt.unpack(bits)[1] == 0 for bits in (a, b)):
                    continue
                for operation, value in (('Add', av + bv), ('Subtract', av - bv), ('Multiply', av * bv)):
                    if 0 < abs(value) < math.ldexp(1.0, 1 - fmt.bias):
                        continue
                    try:
                        packed = struct.pack('>' + code, value)
                    except OverflowError:
                        packed = struct.pack('>' + code, math.copysign(math.inf, value))
                    self.assertEqual(calculate(a, b, fmt, operation)[0], int.from_bytes(packed, 'big'),
                                     (e, precision, operation, a, b))

    def test_zero_signs_nan_priority_and_invalid_operations(self):
        fmt = FloatFormat(8, 24)
        for a, b, op, expected, invalid in (
            (0x80000000, 0x80000000, 'Add', 0x80000000, False),
            (0x80000000, 0, 'Subtract', 0x80000000, False),
            (0x80000000, 0x80000000, 'Subtract', 0, False),
            (0x3f800000, 0x3f800000, 'Subtract', 0, False),
            (0, 0xbf800000, 'Multiply', 0x80000000, False),
            (1, 0x7f800000, 'Multiply', 0x7fc00000, True),
            (0x7f800000, 0xff800000, 'Add', 0x7fc00000, True),
            (0x7f800000, 0x7f800000, 'Subtract', 0x7fc00000, True),
            (0x7f800001, 0, 'Multiply', 0x7fc00000, False),
            (0xff800001, 0xff800000, 'Add', 0x7fc00000, False)):
            result, flags = calculate(a, b, fmt, op)
            self.assertEqual(result, expected)
            self.assertEqual(flags, {'underflow': False, 'overflow': False, 'invalid_op': invalid})

    def test_rounding_ties_carry_and_underflow_rule_are_explicit(self):
        fmt = FloatFormat(8, 24)
        for a, b, op, value, underflow, overflow in (
            (0x3f800000, 0x33800000, 'Add', 0x3f800000, False, False),
            (0x3f800001, 0x33800000, 'Add', 0x3f800002, False, False),
            (0x3fffffff, 0x33800000, 'Add', 0x40000000, False, False),
            (0x7f7fffff, 0x7f7fffff, 'Add', 0x7f800000, False, True),
            (0x00800001, 0x00800000, 'Subtract', 0, True, False),
            (0x00800000, 0x3f000000, 'Multiply', 0, True, False),
            (0x00800000, 0x3f7fffff, 'Multiply', 0, True, False),
            (0x00800001, 0x3f7ffffe, 'Multiply', 0x00800000, False, False)):
            result, flags = calculate(a, b, fmt, op)
            self.assertEqual((result, flags), (value, {'underflow': underflow, 'overflow': overflow, 'invalid_op': False}))

    def test_wide_exponents_and_input_padding_do_not_use_host_float(self):
        fmt = FloatFormat(16, 64)
        one = fmt.pack(0, fmt.bias, 0)
        for value in (fmt.pack(0, 1, 0), fmt.infinity(0) - 1, fmt.pack(1, fmt.bias, 123456789)):
            self.assertEqual(calculate(value, one, fmt, 'Multiply')[0], value)
            self.assertEqual(calculate(value, value, fmt, 'Subtract')[0], 0)
        maximum, minimum = fmt.infinity(0) - 1, fmt.pack(0, 1, 0)
        self.assertEqual(calculate(maximum, minimum, fmt, 'Add')[0], maximum)
        small = FloatFormat(4, 5)
        for padding in (0, 0xfe00):
            self.assertEqual(calculate(0x70 | padding, 0x70 | padding, small, 'Multiply')[0], 0x70)

    def test_programmable_modes_and_only_upper_two_opcode_bits_are_padding(self):
        fmt = FloatFormat(4, 4)
        for code, operation in ((0, 'Add'), (1, 'Subtract')):
            for padding in range(4):
                self.assertEqual(calculate(0x38, 0x40, fmt, 'Both', code | (padding << 6)),
                                 calculate(0x38, 0x40, fmt, operation))
        for code in (2, 4, 32, 63, 255):
            with self.assertRaises(ValueError):
                calculate(0, 0, fmt, 'Both', code)

    def test_sidebands_and_selected_exception_bit_positions(self):
        p = parameters(input_exponent=8, input_fraction=24, a_user_width=3, b_user_width=5,
                       operation_user_width=2, has_a_last=True, has_b_last=True, has_operation_last=True,
                       last_mode='And')
        frame = {'a_tdata': 0x7f800000, 'b_tdata': 0xff800000, 'operation_tdata': 0,
                 'a_tuser': 5, 'b_tuser': 17, 'operation_tuser': 2,
                 'a_tlast': 1, 'b_tlast': 0, 'operation_tlast': 1}
        for mask in range(8):
            chosen = [name for i, name in enumerate(('underflow', 'overflow', 'invalid_op')) if mask & (1 << i)]
            q = {**p, **{'has_' + name: name in chosen for name in ('underflow', 'overflow', 'invalid_op')}}
            wanted = (653 << len(chosen)) | ((1 << chosen.index('invalid_op')) if 'invalid_op' in chosen else 0)
            self.assertEqual(expected_transactions([frame], q), [{'tdata': 0x7fc00000, 'tuser': wanted, 'tlast': 0}])
        q = parameters('Multiply', input_exponent=4, input_fraction=5,
                       has_underflow=False, has_overflow=False, has_invalid_op=False)
        self.assertEqual(expected_transactions([{'a_tdata': 0x170, 'b_tdata': 0x070}], q), [{'tdata': 0xff70}])

    def test_parameter_validation_rejects_coerced_and_inapplicable_options(self):
        describe(parameters())
        describe(parameters('Multiply', input_exponent=11, input_fraction=53,
                            architecture='Low_Latency', mult_usage='Max_Usage'))
        for changes in ({'input_fraction': 65}, {'input_exponent': True}, {'has_invalid_op': 1},
                        {'output_fraction': 4}, {'cycles_per_operation': 2}, {'input_fraction': 64},
                        {'architecture': 'Low_Latency'}, {'mult_usage': 'Full_Usage'},
                        {'has_operation_last': True}, {'add_sub_value': 'Add', 'operation_user_width': 1},
                        {'input_exponent': 8, 'input_fraction': 24, 'mult_usage': 'Max_Usage'},
                        {'input_exponent': 11, 'input_fraction': 53, 'mult_usage': 'Medium_Usage'}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                describe(parameters(**changes))
        for changes in ({'add_sub_value': 'Both'}, {'mult_usage': 'Medium_Usage'},
                        {'architecture': 'Low_Latency'}, {'operation_user_width': 1}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                describe(parameters('Multiply', **changes))
        self.assertEqual(implementation_options('Add_Subtract', 16, 64), [('Speed_Optimized', 'No_Usage')])

    def test_directed_inputs_cover_arithmetic_boundaries_and_opcode_padding(self):
        p = parameters(input_exponent=8, input_fraction=24)
        pairs = set(directed_pairs(p))
        for pair in ((0x3f800000, 0x33800000), (0x3f800001, 0x33800000),
                     (0x00800000, 0x3f7fffff), (0x7f800000, 0), (0x7f800000, 0xff800000)):
            self.assertIn(pair, pairs)
        p = parameters(has_a_last=True, has_b_last=True, has_operation_last=True, last_mode='Or')
        frames = prepare_frames([{'a_tdata': 0, 'b_tdata': 0}], describe(p), p)
        self.assertEqual({row['operation_tdata'] for row in frames}, {0, 1, 64, 65, 128, 129, 192, 193})
        self.assertEqual({(r['a_tlast'], r['b_tlast'], r['operation_tlast']) for r in frames},
                         {(a, b, c) for a in (0, 1) for b in (0, 1) for c in (0, 1)})

    def test_generation_preserves_independent_handshakes_and_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, base = plugin_case('floating_point', Path(directory))
            case = replace(base, case_id='arithmetic_fixture', parameters=parameters(),
                           verification=replace(base.verification, strategy='directed_random', case_budget=256,
                                                coverage_targets=('port_boundaries',)))
            xci = Path(directory) / 'fake.xci'
            xci.write_text('{}')
            with patch('vivado_ip_test.plugins.common.stream.testbench.load_metadata', return_value=(xci, {})):
                artifacts = plugin.generate_testbench(case)
                first = artifacts.testbench_path.read_bytes(), artifacts.input_path.read_bytes(), artifacts.expected_path.read_bytes()
                artifacts = plugin.generate_testbench(case)
            self.assertEqual(first, (artifacts.testbench_path.read_bytes(), artifacts.input_path.read_bytes(), artifacts.expected_path.read_bytes()))
            self.assertEqual(artifacts.metrics['input_lane_count'], 3)
            self.assertFalse(artifacts.metrics['reference_contract']['input_barrier'])
            self.assertTrue(artifacts.metrics['reference_contract']['underflow_documentation_conflict'])
            self.assertIn('accepted_rows(acknowledged(b))', artifacts.testbench_path.read_text())
            manifest = json.loads(artifacts.manifest_path.read_text())
            self.assertEqual(manifest['output_layout']['fields'][0], {'name': 'tdata', 'width': 8})
            schema = json.loads((ROOT/'configs/schemas/ip/floating_point/arithmetic.schema.json').read_text())
            self.assertEqual(set(schema['required']), set(parameters()) - {'add_sub_value'})
            self.assertFalse(schema['additionalProperties'])

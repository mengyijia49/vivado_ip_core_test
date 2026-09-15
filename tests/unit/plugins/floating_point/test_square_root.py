from bisect import bisect_left
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import random
import re
import struct
import math
import unittest

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.stream.testbench import render_testbench
from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from vivado_ip_test.plugins.floating_point.reference import convert, expected_transactions
from vivado_ip_test.plugins.floating_point.vectors import directed_values
from unit.plugins.cycle_helpers import plugin_case


def parameters(exponent=5, precision=11, **changes):
    return {'operation': 'Square_root', 'input_exponent': exponent, 'input_fraction': precision,
            'output_exponent': exponent, 'output_fraction': precision, 'input_unsigned': False,
            'optimization': 'Resources', 'has_last': False, 'user_width': 0,
            'has_underflow': False, 'has_overflow': False, 'has_invalid_op': True, **changes}


def exact_value(bits, fmt):
    sign, exponent, fraction = fmt.unpack(bits)
    return (-1 if sign else 1) * Fraction((1 << fmt.fraction_bits) + fraction) * Fraction(2) ** (
        exponent - fmt.bias - fmt.fraction_bits)


class SquareRootTests(unittest.TestCase):
    def test_special_values_negative_zero_and_signaling_nan(self):
        for bits, output, invalid in ((0, 0, False), (0x8000, 0x8000, False),
            (1, 0, False), (0x83ff, 0x8000, False), (0x7c00, 0x7c00, False),
            (0xfc00, 0x7e00, True), (0xbc00, 0x7e00, True), (0x8400, 0x7e00, True),
            (0x7c01, 0x7e00, False), (0xfc01, 0x7e00, False), (0xffff, 0x7e00, False)):
            self.assertEqual(convert(bits, parameters()),
                             (output, {'underflow': False, 'overflow': False, 'invalid_op': invalid}))

    def test_small_formats_exhaustive_against_rational_midpoint_table(self):
        for precision in (4, 5):
            fmt, p = FloatFormat(4, precision), parameters(4, precision)
            outputs = list(range(1 << fmt.fraction_bits, fmt.infinity(0)))
            values = [exact_value(bits, fmt) for bits in outputs]
            thresholds = [((a + b) / 2) ** 2 for a, b in zip(values, values[1:])]
            for bits in outputs:
                value = exact_value(bits, fmt)
                position = bisect_left(thresholds, value)
                if position < len(thresholds) and thresholds[position] == value and outputs[position] % 2:
                    position += 1
                self.assertEqual(convert(bits, p)[0], outputs[position], (precision, bits))

    def test_all_positive_normal_half_inputs_match_host_sqrt(self):
        p = parameters()
        for bits in range(0x400, 0x7c00):
            value = struct.unpack('>e', bits.to_bytes(2, 'big'))[0]
            expected = int.from_bytes(struct.pack('>e', math.sqrt(value)), 'big')
            self.assertEqual(convert(bits, p)[0], expected, hex(bits))

    def test_wide_results_enclosed_by_exact_squared_midpoints(self):
        rng = random.Random(917)
        for exponent, precision in ((8, 24), (11, 53), (16, 64), (16, 4)):
            fmt, p = FloatFormat(exponent, precision), parameters(exponent, precision)
            for _ in range(400):
                bits = fmt.pack(0, rng.randrange(1, fmt.exponent_mask), rng.getrandbits(fmt.fraction_bits))
                actual, flags = convert(bits, p)
                self.assertFalse(any(flags.values()))
                x, y = exact_value(bits, fmt), exact_value(actual, fmt)
                low = ((exact_value(actual - 1, fmt) + y) / 2) ** 2
                high = ((exact_value(actual + 1, fmt) + y) / 2) ** 2
                self.assertLessEqual(low, x)
                self.assertLessEqual(x, high)
                if x in (low, high):
                    self.assertEqual(actual % 2, 0)

    def test_flag_sidebands_and_signed_byte_padding_are_not_masked(self):
        p = parameters(4, 5, has_last=True, user_width=256)
        frames = [{'tdata': 0xff01, 'tlast': 1, 'tuser': 2**256 - 1},
                  {'tdata': 0x70, 'tlast': 0, 'tuser': 7},
                  {'tdata': 0x170, 'tlast': 1, 'tuser': 5}]
        self.assertEqual(expected_transactions(frames, p),
            [{'tdata': 0xff00, 'tlast': 1, 'tuser': (2**256 - 1) * 2},
             {'tdata': 0x70, 'tlast': 0, 'tuser': 14},
             {'tdata': 0xf8, 'tlast': 1, 'tuser': 11}])
        self.assertEqual(frames[0]['tdata'], 0xff01)

    def test_directed_values_cover_square_neighbors_and_extreme_exponents(self):
        values = set(directed_values(parameters()))
        for square in (0x3c00, 0x4400, 0x4880, 0x4c00):
            for delta in (-1, 0, 1):
                self.assertIn(square + delta, values)
        for bits in (0x0400, 0x7bff, 0x7c01, 0x8000, 0x83ff, 0xfc00):
            self.assertIn(bits, values)
        self.assertEqual(directed_values(parameters()), sorted(values))

    def test_rate_validation_and_old_operation_defaults(self):
        plugin, old = plugin_case('floating_point')
        original = dict(old.parameters)
        self.assertEqual(plugin.describe(old.parameters), plugin.describe({**old.parameters, 'cycles_per_operation': 1}))
        self.assertEqual(dict(old.parameters), original)
        for precision in (4, 11, 24, 53, 64):
            for rate in (1, 2, precision + 1):
                spec = plugin.describe(parameters(16, precision, cycles_per_operation=rate))
                self.assertEqual(spec.settings['C_Rate'], rate)
                self.assertEqual(spec.model_parameters['C_RATE'], rate)
                self.assertEqual(spec.model_parameters['C_HAS_SQRT'], 1)
            with self.assertRaises(PluginError):
                plugin.describe(parameters(16, precision, cycles_per_operation=precision + 2))
        for change in ({'cycles_per_operation': True}, {'cycles_per_operation': 0},
                       {'output_fraction': 12}, {'has_underflow': True}, {'has_overflow': True},
                       {'input_unsigned': True}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                plugin.describe(parameters(**change))
        with self.assertRaises(PluginError):
            plugin.describe({**old.parameters, 'cycles_per_operation': 2})

    def test_long_interval_watchdog_and_tail_observation(self):
        plugin, _ = plugin_case('floating_point')
        spec = plugin.describe(parameters(16, 64, cycles_per_operation=65))
        paths = {name: Path('/tmp') / name for name in ('input_vectors', 'gaps', 'ready', 'accepted_input',
                 'expected_output', 'actual_output', 'protocol_events', 'protocol_summary')}
        text = render_testbench(spec, paths, 4096, 8, 100)
        timeout = int(re.search(r'watchdog : process\s+begin\s+wait for (\d+) ns;', text).group(1))
        self.assertGreater(timeout, 4096 * (65 + 8) * 10)
        self.assertIn('drain_cycles = 274', text)
        self.assertIn('output changed under backpressure', text)
        default = render_testbench(replace(spec, transfer_interval_cycles=1, drain_cycles=64), paths, 4096, 8, 100)
        self.assertIn(f'wait for {1000 + 1000 + (4096 + 1024) * 40 * 10} ns;', default)

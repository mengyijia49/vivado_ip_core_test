from fractions import Fraction
import random
import struct
import unittest

from vivado_ip_test.plugins.floating_point.formats import FloatFormat, encode_float, round_binary, sign_extend
from vivado_ip_test.plugins.floating_point.reference import convert, expected_transactions
from vivado_ip_test.plugins.floating_point.vectors import directed_values


BASE = {"operation": "Float_to_float", "input_exponent": 8, "input_fraction": 24,
        "output_exponent": 5, "output_fraction": 11, "input_unsigned": False,
        "has_underflow": True, "has_overflow": True, "has_invalid_op": False,
        "has_last": False, "user_width": 0}


def f32(value):
    return int.from_bytes(struct.pack('>f', value), 'big')


class FloatingReferenceTests(unittest.TestCase):
    def test_rounding_ties_carries_and_signed_padding(self):
        self.assertEqual([round_binary(i, -1) for i in range(10)], [0, 0, 1, 2, 2, 2, 3, 4, 4, 4])
        fmt = FloatFormat(5, 4)
        self.assertEqual(encode_float(0, 31, -1, fmt)[0], fmt.pack(0, 19, 0))
        self.assertEqual(sign_extend(0x100, 9), 0xff00)
        self.assertEqual(sign_extend(0xff, 9), 0xff)

    def test_float_conversion_special_values_and_underflow_after_rounding(self):
        for source, result in ((0, 0), (0x80000000, 0x8000), (1, 0), (0x807fffff, 0x8000),
                               (0x7f800000, 0x7c00), (0xff800000, 0xfc00),
                               (0x7f800001, 0x7e00), (0xffffffff, 0x7e00)):
            actual, flags = convert(source, BASE)
            self.assertEqual(actual, result)
            self.assertFalse(any(flags.values()))
        output, flags = convert(f32(2**-14 - 2**-25), BASE)
        self.assertEqual(output, 0)
        self.assertTrue(flags['underflow'])
        self.assertEqual(convert(0x387fefff, BASE)[0], 0)
        self.assertEqual(convert(0x387ff000, BASE), (0x400, {'underflow': False, 'overflow': False, 'invalid_op': False}))
        self.assertEqual(convert(0xb87ff000, BASE)[0], 0x8400)
        self.assertEqual(convert(f32(2**-14), BASE)[0], 0x400)
        self.assertEqual(convert(f32(65520), BASE), (0x7c00, {'underflow': False, 'overflow': True, 'invalid_op': False}))

    def test_normal_conversion_matches_independent_host_ieee_rounding(self):
        rng = random.Random(2026)
        for _ in range(6000):
            bits = rng.getrandbits(32)
            exponent = bits >> 23 & 255
            if exponent in (0, 255):
                continue
            value = struct.unpack('>f', bits.to_bytes(4, 'big'))[0]
            if abs(value) < 2**-14:
                continue
            try:
                expected = int.from_bytes(struct.pack('>e', value), 'big')
            except OverflowError:
                expected = 0xfc00 if value < 0 else 0x7c00
            self.assertEqual(convert(bits, BASE)[0], expected)

    def test_fixed_to_float_matches_integer_to_double_for_signed_and_unsigned(self):
        rng = random.Random(42)
        for unsigned in (False, True):
            p = {**BASE, 'operation': 'Fixed_to_float', 'input_exponent': 64, 'input_fraction': 0,
                 'output_exponent': 11, 'output_fraction': 53, 'input_unsigned': unsigned}
            for bits in [0, 1, 2**63, 2**64 - 1, *(rng.getrandbits(64) for _ in range(1000))]:
                value = bits if unsigned or bits < 2**63 else bits - 2**64
                expected = int.from_bytes(struct.pack('>d', float(value)), 'big')
                self.assertEqual(convert(bits, p)[0], expected)

    def test_float_to_fixed_rounding_saturation_and_exceptions(self):
        p = {**BASE, 'operation': 'Float_to_fixed', 'output_exponent': 8, 'output_fraction': 0}
        for value, result, overflow in ((2.5, 2, False), (3.5, 4, False), (-2.5, 254, False),
                                       (127.5, 127, True), (127.4, 127, False),
                                       (-128.5, 128, False), (-128.6, 128, True)):
            actual, flags = convert(f32(value), p)
            self.assertEqual((actual, flags['overflow'], flags['invalid_op']), (result, overflow, False))
        for bits, result, overflow in ((0x7f800000, 127, True), (0xff800000, 128, True),
                                       (0x7fc00000, 128, False), (0xff800001, 128, False)):
            actual, flags = convert(bits, p)
            self.assertEqual((actual, flags['overflow'], flags['invalid_op']), (result, overflow, True))

    def test_small_format_fixed_conversion_exhaustive_fraction_oracle(self):
        p = {**BASE, 'operation': 'Float_to_fixed', 'input_exponent': 4, 'input_fraction': 4,
             'output_exponent': 2, 'output_fraction': 2}
        for bits in range(256):
            sign, exponent, mantissa = bits >> 7, bits >> 3 & 15, bits & 7
            if exponent == 15:
                continue
            value = Fraction(0) if exponent == 0 else Fraction(8 + mantissa, 8) * Fraction(2)**(exponent - 7)
            rounded = round((-value if sign else value) * 4)
            expected = min(7, max(-8, rounded)) & 15
            self.assertEqual(convert(bits, p)[0], expected)

    def test_absolute_preserves_signaling_nan_and_subnormal_payload(self):
        p = {**BASE, 'operation': 'Absolute', 'output_exponent': 8, 'output_fraction': 24}
        for bits in (0x80000001, 0xff800001, 0xffc12345, 0x80000000, 0xff7fffff):
            result, flags = convert(bits, p)
            self.assertEqual(result, bits & 0x7fffffff)
            self.assertFalse(any(flags.values()))

    def test_sidebands_exception_packing_and_input_padding(self):
        p = {**BASE, 'operation': 'Float_to_fixed', 'output_exponent': 4, 'output_fraction': 0,
             'has_underflow': False, 'has_invalid_op': True, 'has_last': True, 'user_width': 3}
        frames = [{'tdata': 0x7f800000, 'tlast': 1, 'tuser': 5}, {'tdata': 0x7fc00000, 'tlast': 0, 'tuser': 2}]
        self.assertEqual(expected_transactions(frames, p),
                         [{'tdata': 7, 'tlast': 1, 'tuser': 23}, {'tdata': 248, 'tlast': 0, 'tuser': 10}])
        self.assertEqual(frames[0]['tdata'], 0x7f800000)
        narrow = {**BASE, 'input_exponent': 4, 'input_fraction': 5, 'output_exponent': 4, 'output_fraction': 5}
        self.assertEqual(convert(0x1fff, narrow), convert(0x1ff, narrow))

    def test_directed_inputs_include_rounding_and_exception_boundaries(self):
        values = set(directed_values(BASE))
        for value in (0, 0x80000000, 0x7f800001, 0xff800000, f32(1 + 2**-11),
                      f32(1 + 2**-11) - 1, f32(1 + 2**-11) + 1, f32(65520)):
            self.assertIn(value, values)

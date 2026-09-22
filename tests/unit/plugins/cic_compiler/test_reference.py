import unittest

from vivado_ip_test.plugins.cic_compiler.reference import (
    causal_input_counts, cic_values, encode_signed, expected_transactions,
    full_precision_width)


class CicReferenceTests(unittest.TestCase):
    def test_full_precision_width_matches_integer_gain(self):
        self.assertEqual(full_precision_width("Decimation", 8, 3, 2, 5), 18)
        self.assertEqual(full_precision_width("Decimation", 2, 6, 2, 16), 32)
        self.assertEqual(full_precision_width("Interpolation", 8, 3, 2, 5), 16)
        self.assertEqual(full_precision_width("Interpolation", 32, 6, 2, 16), 58)

    def test_decimator_impulse_and_constant_gain(self):
        parameters = {"filter_type": "Decimation", "input_width": 8, "stages": 2,
                      "differential_delay": 1, "rate": 4}
        self.assertEqual(cic_values([1] + [0] * 11, parameters), [1, 3, 0])
        outputs = cic_values([1] * 16, parameters)
        self.assertEqual(outputs[-2:], [16, 16])

        frames = [{"tdata": 1}] * 12
        expected = expected_transactions(frames, parameters)
        self.assertEqual(causal_input_counts(frames, expected, parameters), [1, 5, 9])

    def test_interpolator_impulse_and_causal_mapping(self):
        parameters = {"filter_type": "Interpolation", "input_width": 8, "stages": 2,
                      "differential_delay": 1, "rate": 4}
        self.assertEqual(cic_values([1, 0], parameters), [1, 2, 3, 4, 3, 2, 1, 0])
        frames = [{"tdata": 1}, {"tdata": 0}]
        expected = expected_transactions(frames, parameters)
        self.assertEqual(causal_input_counts(frames, expected, parameters), [1] * 4 + [2] * 4)

    def test_negative_values_are_sign_extended_to_axis_bytes(self):
        self.assertEqual(encode_signed(-1, 12), 0xffff)
        self.assertEqual(encode_signed(-128, 8), 0x80)

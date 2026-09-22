from copy import deepcopy
import unittest

from vivado_ip_test.plugins.fir_compiler.reference import (
    expected_transactions,
    mathematical_output_width,
    signed_value,
    vendor_output_width,
)


class FirReferenceTests(unittest.TestCase):
    def test_convolution_uses_zero_history_and_preserves_sidebands(self):
        parameters = {"data_width": 8, "coefficients": [1, -2, 3]}
        frames = [
            {"tdata": value & 0xFF, "tlast": index == 2, "tuser": index + 4}
            for index, value in enumerate((-128, 2, -1))
        ]
        before = deepcopy(frames)
        result = expected_transactions(frames, parameters)
        self.assertEqual([signed_value(row["tdata"], 16) for row in result], [-128, 258, -389])
        self.assertEqual([row["tlast"] for row in result], [False, False, True])
        self.assertEqual([row["tuser"] for row in result], [4, 5, 6])
        self.assertEqual(frames, before)

    def test_full_precision_width_exposes_twos_complement_positive_boundary(self):
        self.assertEqual(vendor_output_width(8, [-8, 0, 0]), 11)
        self.assertEqual(mathematical_output_width(8, [-8, 0, 0]), 12)
        self.assertEqual(vendor_output_width(8, [-1, -1, -2]), 10)
        self.assertEqual(mathematical_output_width(8, [-1, -1, -2]), 11)
        self.assertEqual(vendor_output_width(8, [1, 1, 2]), 10)
        self.assertEqual(mathematical_output_width(8, [1, 1, 2]), 10)

    def test_signed_decode(self):
        self.assertEqual([signed_value(value, 8) for value in (0, 127, 128, 255)], [0, 127, -128, -1])

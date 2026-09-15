from copy import deepcopy
from decimal import Decimal, localcontext, ROUND_FLOOR, ROUND_HALF_UP, ROUND_HALF_EVEN
from random import Random
import unittest

from vivado_ip_test.plugins.cordic.reference import quantized_root, scale_ratio, expected_transactions
from vivado_ip_test.plugins.cordic.vectors import prepare_frames, square_root_boundaries
from unit.plugins.cycle_helpers import plugin_case


class CordicReferenceTests(unittest.TestCase):
    def test_integer_rounding_and_output_carry(self):
        for value, truncated, rounded in ((0, 0, 0), (1, 1, 1), (2, 1, 1), (3, 1, 2),
                                          (32, 5, 6), (224, 14, 15), (225, 15, 15), (255, 15, 16)):
            self.assertEqual(quantized_root(value, 1, 1, "Truncate"), truncated)
            for mode in ("Round_Pos_Inf", "Round_Pos_Neg_Inf", "Nearest_Even"):
                self.assertEqual(quantized_root(value, 1, 1, mode), rounded)

    def test_fractional_exact_ties_and_neighbors(self):
        for value, even, up in ((0, 0, 0), (1, 0, 1), (2, 1, 1), (8, 1, 1),
                                (9, 2, 2), (10, 2, 2), (24, 2, 2), (25, 2, 3), (26, 3, 3)):
            self.assertEqual(quantized_root(value, 1, 4, "Nearest_Even"), even)
            for mode in ("Round_Pos_Inf", "Round_Pos_Neg_Inf"):
                self.assertEqual(quantized_root(value, 1, 4, mode), up)

    def test_exact_integer_model_agrees_with_high_precision_decimal(self):
        rng = Random(1701)
        modes = {"Truncate": ROUND_FLOOR, "Round_Pos_Inf": ROUND_HALF_UP,
                 "Round_Pos_Neg_Inf": ROUND_HALF_UP, "Nearest_Even": ROUND_HALF_EVEN}
        with localcontext() as context:
            context.prec = 150
            for input_width in (8, 9, 16, 17, 31, 32, 47, 48):
                for output_width in (8, 9, 16, 17, 31, 48):
                    p = dict(data_format="UnsignedFraction", input_width=input_width, output_width=output_width)
                    numerator, denominator = scale_ratio(p)
                    for value in (0, 1, (1 << input_width) - 1, *(rng.randrange(1 << input_width) for _ in range(30))):
                        exact = (Decimal(value) * numerator / denominator).sqrt()
                        for mode, decimal_mode in modes.items():
                            self.assertEqual(quantized_root(value, numerator, denominator, mode),
                                             int(exact.to_integral_value(rounding=decimal_mode)))

    def test_padding_is_ignored_and_sidebands_preserved_without_mutation(self):
        _, case = plugin_case("cordic")
        p = {**case.parameters, "input_width": 9, "rounding": "Nearest_Even"}
        frames = [{"tdata": 32, "tlast": 1, "tuser": 7}, {"tdata": 32 | 0xFE00, "tlast": 0, "tuser": 1}]
        before = deepcopy(frames)
        self.assertEqual(expected_transactions(frames, p),
                         [{"tdata": 6, "tlast": 1, "tuser": 7}, {"tdata": 6, "tlast": 0, "tuser": 1}])
        self.assertEqual(frames, before)

    def test_output_field_is_sign_extended_even_for_unsigned_data(self):
        _, case = plugin_case("cordic")
        p = {**case.parameters, "rounding": "Round_Pos_Inf"}
        self.assertEqual(expected_transactions([{"tdata": 255}], p), [{"tdata": 240}])
        p = {**p, "input_width": 9, "output_width": 9, "data_format": "UnsignedFraction"}
        self.assertEqual(expected_transactions([{"tdata": 256}], p), [{"tdata": 65280}])

    def test_directed_sequence_crosses_square_and_halfway_boundaries(self):
        plugin, case = plugin_case("cordic")
        p = {**case.parameters, "data_format": "UnsignedFraction", "input_width": 17,
             "output_width": 8, "has_last": True, "user_width": 3}
        values = set(square_root_boundaries(p))
        self.assertTrue({0, 1, 2, 3, 4, 5, 8, 9, 10, 24, 25, 26}.issubset(values))
        spec = plugin.describe(p)
        frames = [{"tdata": 7, "tlast": 1, "tuser": 0}]
        result = prepare_frames(frames, spec, p)
        self.assertEqual(result[-1], frames[0])
        self.assertIsNot(result[-1], frames[0])
        self.assertEqual({f["tdata"] & 0xFFFE0000 for f in result}, {0, 0xFE0000})
        for left, right in zip(result[:-1:2], result[1:-1:2]):
            self.assertEqual(left["tdata"] & 0x1FFFF, right["tdata"] & 0x1FFFF)

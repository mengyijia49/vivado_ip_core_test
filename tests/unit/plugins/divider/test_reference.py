import unittest

from vivado_ip_test.domain import VerificationProfile
from vivado_ip_test.plugins.divider.reference import (
    DivisionResult,
    encode_fixed_width,
    pack_remainder_output,
    truncating_division,
)
from vivado_ip_test.plugins.divider.vectors import generate_vectors
from vivado_ip_test.strategies import create_default_strategy_registry


class DividerReferenceTests(unittest.TestCase):
    def test_unsigned_division(self):
        self.assertEqual(
            truncating_division(100, 9),
            DivisionResult(quotient=11, remainder=1),
        )

    def test_signed_division_truncates_toward_zero(self):
        self.assertEqual(
            truncating_division(-100, 9),
            DivisionResult(quotient=-11, remainder=-1),
        )
        self.assertEqual(
            truncating_division(100, -9),
            DivisionResult(quotient=-11, remainder=1),
        )

    def test_fixed_width_encoding_and_output_packing(self):
        result = DivisionResult(quotient=-11, remainder=-1)

        self.assertEqual(encode_fixed_width(-1, 8), 0xFF)
        self.assertEqual(pack_remainder_output(result, 16, 8), 0xFFF5FF)

    def test_vector_generation_is_reproducible_and_excludes_zero_divisors(self):
        arguments = {
            "dividend_width": 16,
            "divisor_width": 8,
            "operand_sign": "Signed",
            "profile": VerificationProfile(
                strategy="directed_random",
                strategy_version="1.0",
                random_seed=42,
                case_budget=32,
                coverage_targets=("boundary_values",),
            ),
            "strategy_registry": create_default_strategy_registry(),
        }

        first, first_generation = generate_vectors(**arguments)
        second, second_generation = generate_vectors(**arguments)

        self.assertEqual(first, second)
        self.assertEqual(first_generation, second_generation)
        self.assertTrue(all(vector.divisor != 0 for vector in first))
        self.assertEqual(len(first), len({(v.dividend, v.divisor) for v in first}))

    def test_unsigned_sign_target_and_exhaustive_count_are_measured(self):
        vectors, result = generate_vectors(
            dividend_width=2, divisor_width=2, operand_sign="Unsigned",
            profile=VerificationProfile(
                strategy="exhaustive", strategy_version="1.0", random_seed=0,
                case_budget=12, coverage_targets=("boundary_values", "sign_combinations", "nonzero_divisor"),
            ),
            strategy_registry=create_default_strategy_registry(),
        )
        self.assertEqual(len(vectors), 12)
        self.assertEqual(result.missing_targets, ())
        targets = result.coverage_metrics["target_coverage"]
        self.assertEqual(targets["sign_combinations"]["total_count"], 1)
        self.assertEqual(targets["boundary_values"]["total_count"], 3)

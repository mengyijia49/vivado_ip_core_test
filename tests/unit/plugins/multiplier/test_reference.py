import unittest

from vivado_ip_test.domain import VerificationProfile
from vivado_ip_test.plugins.multiplier.reference import (
    encode_fixed_width,
    multiply,
)
from vivado_ip_test.plugins.multiplier.vectors import generate_vectors
from vivado_ip_test.strategies import create_default_strategy_registry


class MultiplierReferenceTests(unittest.TestCase):
    def test_multiplies_signed_and_unsigned_values(self):
        self.assertEqual(multiply(-128, 255), -32640)
        self.assertEqual(multiply(255, 255), 65025)

    def test_encodes_negative_product_as_twos_complement(self):
        self.assertEqual(encode_fixed_width(-2, 16), 0xFFFE)

    def test_vector_generation_is_reproducible_and_covers_boundaries(self):
        profile = VerificationProfile(
            strategy="directed_random",
            strategy_version="1.0",
            random_seed=17,
            case_budget=24,
            coverage_targets=("boundary_values",),
        )
        arguments = {
            "a_width": 8,
            "b_width": 8,
            "a_type": "Signed",
            "b_type": "Unsigned",
            "output_width": 16,
            "profile": profile,
            "strategy_registry": create_default_strategy_registry(),
        }

        first, first_generation = generate_vectors(**arguments)
        second, second_generation = generate_vectors(**arguments)

        self.assertEqual(first, second)
        self.assertEqual(first_generation, second_generation)
        self.assertIn((-128, 255), [(vector.a, vector.b) for vector in first])
        self.assertEqual(len(first), len({(vector.a, vector.b) for vector in first}))

    def test_exhaustive_small_space_hits_all_declared_bins(self):
        for a_type, b_type in (("Unsigned", "Unsigned"), ("Signed", "Unsigned"), ("Signed", "Signed")):
            with self.subTest(a_type=a_type, b_type=b_type):
                _, result = generate_vectors(
                    a_width=2, b_width=2, a_type=a_type, b_type=b_type,
                    output_width=4,
                    profile=VerificationProfile(
                        strategy="exhaustive", strategy_version="1.0", random_seed=0,
                        case_budget=16,
                        coverage_targets=("boundary_values", "sign_combinations", "full_precision", "operand_magnitude", "complete_input_space"),
                    ),
                    strategy_registry=create_default_strategy_registry(),
                )
                self.assertEqual(result.missing_targets, ())
                self.assertEqual(result.coverage_metrics["input_space_fraction"], 1.0)

    def test_guided_magnitude_coverage_is_reproducible(self):
        arguments = dict(
            a_width=8, b_width=8, a_type="Unsigned", b_type="Unsigned", output_width=16,
            profile=VerificationProfile(
                strategy="coverage_guided", strategy_version="1.0", random_seed=20260917,
                case_budget=41, coverage_targets=("operand_magnitude",),
            ),
            strategy_registry=create_default_strategy_registry(),
        )
        first = generate_vectors(**arguments)
        self.assertEqual(first, generate_vectors(**arguments))
        coverage = first[1].coverage_metrics["target_coverage"]["operand_magnitude"]
        self.assertEqual(coverage["hit_count"], 18)
        self.assertEqual(coverage["total_count"], 18)

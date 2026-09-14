import unittest
from dataclasses import replace

from vivado_ip_test.domain import VerificationProfile
from vivado_ip_test.strategies import (
    CaseSpace,
    DirectedRandomStrategy,
    ExhaustiveStrategy,
    StrategyError,
    StrategyRegistry,
    create_default_strategy_registry,
)


def make_space():
    return CaseSpace(
        directed_cases=(0, 3),
        random_case=lambda generator: generator.randrange(4),
        exhaustive_cases=lambda: range(4),
        total_case_count=4,
        coverage_features=lambda case: frozenset(
            {"even" if case % 2 == 0 else "odd"}
        ),
    )


def make_profile(strategy, budget, version="1.0"):
    return VerificationProfile(
        strategy=strategy,
        strategy_version=version,
        random_seed=19,
        case_budget=budget,
        coverage_targets=("boundary_values",),
    )


class StrategyTests(unittest.TestCase):
    def test_directed_random_is_reproducible_and_keeps_directed_prefix(self):
        registry = create_default_strategy_registry()
        profile = make_profile("directed_random", 3)

        first = registry.generate(make_space(), profile)
        second = registry.generate(make_space(), profile)

        self.assertEqual(first, second)
        self.assertEqual(first.cases[:2], (0, 3))
        self.assertEqual(len(set(first.cases)), 3)

    def test_directed_random_rejects_budget_below_directed_set(self):
        with self.assertRaisesRegex(StrategyError, "小于定向用例数"):
            DirectedRandomStrategy().generate(
                make_space(), make_profile("directed_random", 1)
            )

    def test_exhaustive_returns_complete_input_space(self):
        result = ExhaustiveStrategy().generate(
            make_space(), make_profile("exhaustive", 4)
        )

        self.assertEqual(result.cases, (0, 1, 2, 3))
        self.assertEqual(result.generated_count, 4)

    def test_exhaustive_rejects_insufficient_budget(self):
        with self.assertRaisesRegex(StrategyError, "穷举策略需要"):
            ExhaustiveStrategy().generate(
                make_space(), make_profile("exhaustive", 3)
            )

    def test_registry_rejects_version_mismatch(self):
        registry = create_default_strategy_registry()

        with self.assertRaisesRegex(StrategyError, "版本不匹配"):
            registry.generate(
                make_space(), make_profile("directed_random", 3, "2.0")
            )

    def test_registry_rejects_duplicate_name(self):
        registry = StrategyRegistry()
        registry.register(DirectedRandomStrategy())

        with self.assertRaisesRegex(StrategyError, "重复注册"):
            registry.register(DirectedRandomStrategy())

    def test_coverage_guided_prefers_uncovered_features(self):
        registry = create_default_strategy_registry()
        profile = VerificationProfile(
            strategy="coverage_guided",
            strategy_version="1.0",
            random_seed=19,
            case_budget=2,
            coverage_targets=("classes",),
        )
        space = replace(
            make_space(), directed_cases=(0,),
            coverage_features=lambda case: frozenset({"rare" if case == 3 else "common"}),
            target_bins={"classes": frozenset({"common", "rare"})},
        )
        result = registry.generate(space, profile)

        self.assertEqual(result.cases, (0, 3))
        self.assertEqual(result, registry.generate(space, profile))
        self.assertEqual(result.covered_targets, ("classes",))
        self.assertEqual(result.missing_targets, ())

    def test_all_strategies_use_identical_coverage_measurement(self):
        registry = create_default_strategy_registry()
        metrics = []
        for strategy in ("directed_random", "coverage_guided", "exhaustive"):
            result = registry.generate(
                make_space(), replace(make_profile(strategy, 4), coverage_targets=("even", "odd", "complete_input_space"))
            )
            self.assertEqual(result.covered_targets, ("complete_input_space", "even", "odd"))
            metrics.append(result.coverage_metrics)
        self.assertEqual(metrics[0], metrics[1])
        self.assertEqual(metrics[1], metrics[2])
        self.assertEqual(metrics[0]["input_space_fraction"], 1.0)

    def test_partial_target_is_not_reported_as_complete(self):
        result = create_default_strategy_registry().generate(
            replace(make_space(), target_bins={"classes": frozenset({"even", "odd", "unseen"})}),
            replace(make_profile("directed_random", 2), coverage_targets=("classes", "complete_input_space")),
        )
        self.assertEqual(result.covered_targets, ())
        self.assertEqual(result.missing_targets, ("classes", "complete_input_space"))
        coverage = result.coverage_metrics["target_coverage"]
        self.assertEqual(coverage["classes"]["hit_count"], 2)
        self.assertEqual(coverage["classes"]["total_count"], 3)
        self.assertEqual(coverage["complete_input_space"]["fraction"], 0.5)

    def test_guided_fallback_completes_saturated_input_space(self):
        result = create_default_strategy_registry().generate(
            replace(make_space(), random_case=lambda generator: 0),
            make_profile("coverage_guided", 4),
        )
        self.assertEqual(set(result.cases), {0, 1, 2, 3})

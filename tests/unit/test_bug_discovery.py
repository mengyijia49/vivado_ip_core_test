from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from vivado_ip_test.configuration import ConfigError, load_test_cases
from vivado_ip_test.domain import VerificationProfile
from vivado_ip_test.plugins.divider.vectors import generate_vectors as divider_vectors
from vivado_ip_test.plugins.multiplier.vectors import generate_vectors as multiplier_vectors
from vivado_ip_test.services.failure_analysis import analyze_outputs
from vivado_ip_test.services.stimulus_schedule import build_schedule
from vivado_ip_test.strategies import create_default_strategy_registry
from vivado_ip_test.strategies.boundaries import boundary_values
from unit import test_configuration
from unit.test_configuration import valid_config


def profile(**changes):
    return replace(VerificationProfile("directed_random", "1.0", 42, 65536,
                                      ("systematic_values",), boundary_mode="systematic"), **changes)


class ExplorationConfigurationTests(unittest.TestCase):
    def load(self, config):
        return test_configuration.ConfigurationTests().load(config)

    def test_expands_unique_cases_and_keeps_parameters(self):
        config = valid_config()
        config["exploration"] = {"seeds": [1, 2], "timing_modes": ["continuous", "random_gaps", "bursts"]}
        cases = self.load(config)
        self.assertEqual(len(cases), 6)
        self.assertEqual(len({case.case_id for case in cases}), 6)
        self.assertEqual(cases[4].verification.timing_mode, "random_gaps")
        self.assertEqual(cases[4].verification.random_seed, 2)
        self.assertEqual(cases[4].parameters, cases[0].parameters)

    def test_rejects_invalid_exploration_options(self):
        for exploration in (
            {}, {"seeds": [1, 1], "timing_modes": ["bursts"]},
            {"seeds": [True], "timing_modes": ["bursts"]},
            {"seeds": [-1], "timing_modes": ["bursts"]},
            {"seeds": [], "timing_modes": ["bursts"]},
            {"seeds": [1], "timing_modes": ["unknown"]},
            {"seeds": [1], "timing_modes": [[], "continuous"]},
        ):
            with self.subTest(exploration=exploration), self.assertRaises(ConfigError):
                config = valid_config()
                config["exploration"] = exploration
                self.load(config)

    def test_rejects_invalid_timing_and_boundary_fields(self):
        for name, value in (("boundary_mode", []), ("timing_mode", "bad"),
                            ("input_order", "bad"), ("max_gap_cycles", True),
                            ("max_gap_cycles", -1), ("burst_length", 0)):
            with self.subTest(name=name, value=value), self.assertRaises(ConfigError):
                config = valid_config()
                config["cases"][0]["verification"][name] = value
                self.load(config)

    def test_default_profile_roundtrips_through_effective_config(self):
        config = valid_config()
        case = self.load(config)[0]
        config["cases"][0]["verification"] = case.verification.as_dict()
        self.assertEqual(self.load(config)[0], case)


class BoundaryGenerationTests(unittest.TestCase):
    def test_patterns_powers_and_signed_extremes(self):
        for signed in (False, True):
            values = boundary_values(8, signed)
            self.assertEqual(values, tuple(sorted(set(values))))
            self.assertTrue({0, 1, 63, 64, 65, 0x55} <= set(values))
            if signed:
                self.assertTrue({-128, -127, -1, -86, 126, 127} <= set(values))
            else:
                self.assertTrue({0xAA, 0xFE, 0xFF} <= set(values))

    def test_divider_systematic_cases_are_legal_and_cover_relations(self):
        arguments = dict(dividend_width=16, divisor_width=8, operand_sign="Signed",
                         profile=profile(case_budget=12000, coverage_targets=("systematic_values", "division_relations")),
                         strategy_registry=create_default_strategy_registry())
        vectors, result = divider_vectors(**arguments)
        self.assertEqual((vectors, result), divider_vectors(**arguments))
        self.assertFalse(result.missing_targets)
        for vector in vectors:
            self.assertNotEqual(vector.divisor, 0)
            self.assertNotEqual((vector.dividend, vector.divisor), (-32768, -1))
            self.assertEqual(vector.dividend, vector.quotient * vector.divisor + vector.remainder)
            self.assertLess(abs(vector.remainder), abs(vector.divisor))
            self.assertTrue(vector.remainder == 0 or (vector.remainder < 0) == (vector.dividend < 0))

    def test_discovery_matrix_budgets_and_targets_are_executable_without_vivado(self):
        root = Path(__file__).resolve().parents[2]
        cases = load_test_cases(root / "configs/bug_discovery.json")
        self.assertEqual(len(cases), 90)
        total = 0
        for case in cases[::9]:
            with self.subTest(case_id=case.case_id):
                arguments = dict(case.parameters)
                if case.ip_type == "divider":
                    vectors, result = divider_vectors(**arguments, profile=case.verification,
                        strategy_registry=create_default_strategy_registry())
                else:
                    arguments.pop("pipeline_stages")
                    arguments["output_width"] = arguments["a_width"] + arguments["b_width"]
                    vectors, result = multiplier_vectors(**arguments, profile=case.verification,
                        strategy_registry=create_default_strategy_registry())
                self.assertLessEqual(len(vectors), case.verification.case_budget)
                self.assertFalse(result.missing_targets)
                self.assertGreater(result.directed_count, 100)
                total += len(vectors)
        self.assertEqual(total * 9, 5893623)


class TimingScheduleTests(unittest.TestCase):
    def test_continuous_schedule_preserves_baseline(self):
        for can_idle in (False, True):
            schedule = build_schedule(24, profile(), can_idle=can_idle)
            self.assertEqual(schedule.transaction_indices, tuple(range(24)))
            self.assertEqual(schedule.gaps, (0,) * 24)
            self.assertEqual(schedule.input_cycles, 24)

    def test_random_schedule_is_deterministic_and_uses_separate_random_stream(self):
        config = profile(timing_mode="random_gaps", input_order="shuffled")
        first = build_schedule(100, config, can_idle=True)
        self.assertEqual(first, build_schedule(100, config, can_idle=True))
        self.assertGreater(sum(first.gaps), 0)
        self.assertEqual(first.gaps[0], 0)
        self.assertLessEqual(max(first.gaps), config.max_gap_cycles)
        self.assertEqual(first.transaction_indices,
                         build_schedule(100, replace(config, timing_mode="continuous"), can_idle=True).transaction_indices)
        self.assertNotEqual(first.transaction_indices,
                            build_schedule(100, replace(config, random_seed=99), can_idle=True).transaction_indices)

    def test_multiplier_hold_cycles_are_checked_transactions(self):
        schedule = build_schedule(5, profile(timing_mode="bursts", burst_length=2, max_gap_cycles=3), can_idle=False)
        self.assertEqual(schedule.gaps, (0, 0, 3, 0, 3))
        self.assertEqual(schedule.transaction_indices, (0, 1, 1, 1, 1, 2, 3, 3, 3, 3, 4))
        self.assertEqual(schedule.input_cycles, len(schedule.transaction_indices))

    def test_divider_gaps_are_not_transactions(self):
        schedule = build_schedule(5, profile(timing_mode="bursts", burst_length=2, max_gap_cycles=3), can_idle=True)
        self.assertEqual(schedule.transaction_indices, tuple(range(5)))
        self.assertEqual(schedule.input_cycles, 11)


class FailureAnalysisTests(unittest.TestCase):
    def test_maps_failure_after_holds_to_original_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectors").mkdir()
            (root / "outputs").mkdir()
            (root / "vectors/expected_output.txt").write_text("01\n01\n10\n")
            (root / "outputs/actual_output.txt").write_text("01\nXX\n")
            (root / "vectors/schedule.json").write_text(json.dumps({
                "transaction_vector_indices": [1, 1, 0], "timing_mode": "bursts"}))
            (root / "vectors/vectors.json").write_text('[{"a": 0}, {"a": 1}]')
            evidence = analyze_outputs(root)
            self.assertEqual(evidence["classification"], "UNTRIAGED")
            self.assertEqual(evidence["kind"], "value_mismatch")
            self.assertEqual(evidence["output_index"], 1)
            self.assertEqual(evidence["vector_index"], 1)
            self.assertEqual(evidence["input_vector"], {"a": 1})
            self.assertTrue(evidence["contains_unknown_bits"])

    def test_missing_and_extra_outputs(self):
        for actual, kind in (("", "missing_output"), ("01\n10\n", "extra_output")):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "vectors").mkdir()
                (root / "outputs").mkdir()
                (root / "vectors/expected_output.txt").write_text("01\n")
                (root / "outputs/actual_output.txt").write_text(actual)
                self.assertEqual(analyze_outputs(root)["kind"], kind)

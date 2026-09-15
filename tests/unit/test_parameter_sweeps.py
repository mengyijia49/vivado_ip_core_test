from copy import deepcopy
from collections import Counter
from pathlib import Path
import tempfile
import json
import unittest

from vivado_ip_test.configuration import ConfigError, iter_test_cases, load_test_cases
from vivado_ip_test.configuration.uniqueness import UniqueKeys
from vivado_ip_test.configuration.sweeps import expand_sweeps
from vivado_ip_test.infrastructure import RepositoryLayout
from vivado_ip_test.plugins.catalog import create_plugin_registry
from vivado_ip_test.strategies import create_default_strategy_registry
from vivado_ip_test.strategies.boundaries import boundary_values
from vivado_ip_test.plugins.divider.vectors import generate_vectors
from unit.test_configuration import valid_config


class SweepTests(unittest.TestCase):
    def sweep(self):
        case = valid_config()["cases"][0]
        case.pop("case_id")
        return {"case_prefix": "scan", "template": case,
                "axes": {"dividend_width": [16, 32], "operand_sign": ["Unsigned", "Signed"]}}

    def test_product_has_stable_names_and_independent_parameters(self):
        sweep = self.sweep()
        cases = expand_sweeps([sweep])
        self.assertEqual(len(cases), 4)
        self.assertEqual(cases[0]["case_id"], "scan__dividend_width_16__operand_sign_Unsigned")
        cases[0]["parameters"]["divisor_width"] = 1
        self.assertEqual(cases[1]["parameters"]["divisor_width"], 8)
        sweep["axes"]["dividend_width"].reverse()
        self.assertEqual({c["case_id"] for c in cases}, {c["case_id"] for c in expand_sweeps([sweep])})

    def test_rejects_bad_axes_and_excessive_expansion(self):
        for axes in ({}, {"unknown": [1]}, {"dividend_width": []},
                     {"dividend_width": [16, 16]}, {"dividend_width": [{}]},
                     {"dividend_width": list(range(20001))}):
            with self.subTest(axes=str(axes)[:80]), self.assertRaises(ValueError):
                expand_sweeps([{**self.sweep(), "axes": axes}])

    def test_named_arrays_are_independent_and_keep_stable_ids(self):
        sweep = self.sweep()
        sweep["template"]["parameters"]["input_widths"] = [1]
        sweep["axes"] = {"input_widths": [
            {"label": "mixed", "value": [1, 7, 33]}, {"label": "uniform", "value": [8, 8]}],
            "dividend_width": [16, 32]}
        cases = expand_sweeps([sweep])
        names = {c["case_id"] for c in cases}
        self.assertIn("scan__input_widths_mixed__dividend_width_16", names)
        cases[0]["parameters"]["input_widths"][0] = 999
        self.assertEqual(cases[1]["parameters"]["input_widths"], [1, 7, 33])
        self.assertEqual(sweep["axes"]["input_widths"][0]["value"], [1, 7, 33])
        sweep["axes"]["input_widths"].reverse()
        self.assertEqual(names, {c["case_id"] for c in expand_sweeps([sweep])})

    def test_named_large_literals_do_not_expand_the_path(self):
        sweep = self.sweep()
        sweep["axes"] = {"dividend_width": [{"label": "wide", "value": "0x" + "f"*1024}]}
        case = expand_sweeps([sweep])[0]
        self.assertEqual(case["case_id"], "scan__dividend_width_wide")
        self.assertEqual(case["parameters"]["dividend_width"], "0x" + "f"*1024)

    def test_rejects_ambiguous_labels_duplicate_values_and_nested_parameters(self):
        for values in ([1, {"label": "also_one", "value": 1}],
                       [True, "true"],
                       [{"label": "same", "value": 1}, {"label": "same", "value": 2}],
                       [{"label": "a", "value": [1]}, {"label": "b", "value": [1]}],
                       [{"label": "../bad", "value": 1}],
                       [{"label": "empty", "value": []}],
                       [{"label": "nested", "value": [[1]]}],
                       [{"label": "float", "value": [1.5]}],
                       [{"label": "extra", "value": 1, "unknown": 0}]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                expand_sweeps([{**self.sweep(), "axes": {"dividend_width": values}}])

    def test_rejects_mixed_ip_leaf_and_conflicting_formats(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "matrix.json"
            first, second = self.sweep(), deepcopy(self.sweep())
            second["case_prefix"] = "other"
            second["template"]["ip_type"] = "counter"
            path.write_text(json.dumps({"schema_version": 2, "sweeps": [first, second]}))
            with self.assertRaisesRegex(ConfigError, "拆分"):
                load_test_cases(path)
            path.write_text(json.dumps({"schema_version": 2, "sweeps": [first], "cases": []}))
            with self.assertRaisesRegex(ConfigError, "只能选择"):
                load_test_cases(path)

    def test_all_shipped_matrices_validate_without_vivado(self):
        root = Path(__file__).resolve().parents[2]
        registry = create_plugin_registry(RepositoryLayout(root), create_default_strategy_registry())
        counts = Counter()
        with UniqueKeys() as parameters:
            for case in iter_test_cases(root / "configs/extended_discovery.json"):
                with self.subTest(case=case.case_id):
                    self.assertTrue(parameters.add(json.dumps([case.ip_type, dict(case.parameters)], sort_keys=True)))
                    self.assertNotIn("__seed", case.case_id)
                    registry.resolve(case.ip_type).validate_case(case)
                counts[case.ip_type] += 1
        self.assertEqual(len(counts), 36)
        self.assertEqual(sum(counts.values()), 9472890)
        regression = load_test_cases(root / "configs/extended_regression.json")
        self.assertEqual(len(regression), 323)
        self.assertEqual(sum(len(case.stages) for case in regression), 970)

    def test_arithmetic_matrix_budgets_cover_directed_inputs_without_generating_random_data(self):
        root = Path(__file__).resolve().parents[2]

        class Inspected(Exception):
            pass

        class Inspector:
            def generate(inner, space, profile):
                if profile.strategy == "exhaustive":
                    self.assertGreaterEqual(profile.case_budget, space.total_case_count)
                else:
                    self.assertGreaterEqual(profile.case_budget, len(set(space.directed_cases)))
                    self.assertLessEqual(profile.case_budget, space.total_case_count)
                raise Inspected

        for case in load_test_cases(root / "configs/ip/divider/extended.json"):
            with self.subTest(case=case.case_id), self.assertRaises(Inspected):
                generate_vectors(**case.parameters, profile=case.verification, strategy_registry=Inspector())
        for case in load_test_cases(root / "configs/ip/multiplier/extended.json"):
            p = case.parameters
            minimum = len(boundary_values(p["a_width"], p["a_type"] == "Signed")) * len(
                boundary_values(p["b_width"], p["b_type"] == "Signed"))
            space = 1 << (p["a_width"] + p["b_width"])
            with self.subTest(case=case.case_id):
                if case.verification.strategy == "exhaustive":
                    self.assertGreaterEqual(case.verification.case_budget, space)
                else:
                    self.assertLessEqual(minimum, case.verification.case_budget)
                    self.assertLessEqual(case.verification.case_budget, space)

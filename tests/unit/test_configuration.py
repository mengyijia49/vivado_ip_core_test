import json
import tempfile
import unittest
from pathlib import Path

from vivado_ip_test.configuration import ConfigError, load_test_cases
from vivado_ip_test.domain import Stage


def valid_config():
    return {
        "schema_version": 2,
        "cases": [
            {
                "case_id": "arbitrary_case_name",
                "ip_type": "divider",
                "vendor": "xilinx.com",
                "ip_name": "div_gen",
                "parameters": {
                    "dividend_width": 16,
                    "divisor_width": 8,
                    "operand_sign": "Unsigned",
                },
                "stages": ["create_ip", "sim_demo"],
                "verification": {
                    "strategy": "directed_random",
                    "strategy_version": "1.0",
                    "random_seed": 1234,
                    "case_budget": 16,
                    "coverage_targets": ["boundary_values"],
                },
            }
        ],
    }


class ConfigurationTests(unittest.TestCase):
    def test_rejects_mixed_ip_types_in_one_parameter_file(self):
        config = valid_config()
        other = dict(config["cases"][0], case_id="other", ip_type="multiplier")
        config["cases"].append(other)
        with self.assertRaisesRegex(ConfigError, "拆分"):
            self.load(config)

    def test_loads_relative_includes_and_rejects_cycles_and_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child = root / "ip/divider/regression.json"
            child.parent.mkdir(parents=True)
            child.write_text(json.dumps(valid_config()))
            entry = root / "matrix.json"
            entry.write_text(json.dumps({"schema_version": 2, "includes": ["ip/divider/regression.json"]}))
            self.assertEqual(load_test_cases(entry)[0].case_id, "arbitrary_case_name")
            entry.write_text(json.dumps({"schema_version": 2, "includes": ["ip/divider/regression.json"] * 2}))
            with self.assertRaisesRegex(ConfigError, "唯一"):
                load_test_cases(entry)
            child.write_text(json.dumps({"schema_version": 2, "includes": ["../../matrix.json"]}))
            with self.assertRaisesRegex(ConfigError, "循环"):
                load_test_cases(entry)

    def test_rejects_parameters_in_composition_file(self):
        config = valid_config()
        config["includes"] = ["ip/divider/regression.json"]
        with self.assertRaisesRegex(ConfigError, "只能选择"):
            self.load(config)

    def load(self, config):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "matrix.json"
            path.write_text(json.dumps(config))
            return load_test_cases(path)

    def test_loads_versioned_cases(self):
        cases = self.load(valid_config())

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].case_id, "arbitrary_case_name")
        self.assertEqual(cases[0].ip_type, "divider")
        self.assertEqual(cases[0].stages, (Stage.CREATE_IP, Stage.SIM_DEMO))
        self.assertEqual(cases[0].verification.strategy, "directed_random")

    def test_rejects_duplicate_case_ids(self):
        config = valid_config()
        config["cases"].append(dict(config["cases"][0]))

        with self.assertRaisesRegex(ConfigError, "case_id 必须唯一"):
            self.load(config)

    def test_rejects_unknown_schema_version(self):
        config = valid_config()
        config["schema_version"] = 3

        with self.assertRaisesRegex(ConfigError, "schema_version"):
            self.load(config)

    def test_requires_create_ip_as_first_stage(self):
        config = valid_config()
        config["cases"][0]["stages"] = ["sim_demo"]

        with self.assertRaisesRegex(ConfigError, "create_ip"):
            self.load(config)

    def test_requires_testbench_generation_before_selfcheck(self):
        config = valid_config()
        config["cases"][0]["stages"] = ["create_ip", "sim_selfcheck"]

        with self.assertRaisesRegex(ConfigError, "generate_testbench"):
            self.load(config)

    def test_rejects_unknown_case_fields(self):
        config = valid_config()
        config["cases"][0]["unexpected"] = True

        with self.assertRaisesRegex(ConfigError, "未知字段"):
            self.load(config)

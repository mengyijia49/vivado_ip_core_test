from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.metadata import load_metadata, setting_text
from vivado_ip_test.plugins.common.vectors import cycle_space
from vivado_ip_test.plugins.xlconstant.reference import parse_literal
from vivado_ip_test.strategies import create_default_strategy_registry
from unit.plugins.cycle_helpers import plugin_case


class ConstantTests(unittest.TestCase):
    def test_matrix_does_not_count_alternate_literals_as_new_numeric_configurations(self):
        cases = load_test_cases(Path(__file__).resolve().parents[4] / "configs/ip/xlconstant/extended.json")
        parameters = {(c.parameters["width"], parse_literal(c.parameters["value"])) for c in cases}
        self.assertEqual(len(cases), 17161)
        self.assertEqual(len(parameters), len(cases))
        for width in range(1, 4097):
            for value in (0, 1, 1 << (width-1), (1 << width)-1):
                self.assertIn((width, value), parameters)

    def test_documented_literal_formats_use_independent_integer_parser(self):
        for text, value in (("0", 0), ("12", 12), ("b1100", 12), ("014", 12), ("0xC", 12), ("0X0C", 12)):
            self.assertEqual(parse_literal(text), value)
        for text in ("", "-1", "+1", " 1", "1 ", "0b11", "09", "b102", "0x", "1_000", 1):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_literal(text)

    def test_rejects_out_of_range_values_widths_and_fake_inputs(self):
        plugin, _ = plugin_case("xlconstant")
        for p in ({"width": 0, "value": "0"}, {"width": 4097, "value": "0"},
                  {"width": True, "value": "0"}, {"width": 3, "value": "8"}, {"width": 3, "value": 7}):
            with self.subTest(p=p), self.assertRaises(PluginError):
                plugin.describe(p)
        with self.assertRaises(ValueError):
            plugin.describe({"width": 1, "value": "1"}).model_factory().step({"fake": 0})

    def test_inputless_space_has_one_state_under_all_strategies(self):
        plugin, case = plugin_case("xlconstant")
        spec = plugin.describe(case.parameters)
        space = cycle_space(spec, False)
        self.assertEqual((space.total_case_count, space.directed_cases), (1, ((),)))
        for strategy in ("exhaustive", "directed_random", "coverage_guided"):
            profile = replace(case.verification, strategy=strategy)
            generation = create_default_strategy_registry().generate(space, profile)
            self.assertEqual(generation.cases, ((),))
            self.assertEqual(generation.as_dict()["target_coverage"]["complete_input_space"]["total_count"], 1)
        for changes in ({"case_budget": 2}, {"timing_mode": "random_gaps"}, {"coverage_targets": ("port_boundaries",)}):
            with self.assertRaises(PluginError):
                plugin.validate_case(replace(case, verification=replace(case.verification, **changes)))

    def test_inputless_backend_does_not_create_zero_width_vectors_or_count_transfers(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("xlconstant", Path(directory))
            xci = Path(directory)/"fake.xci"
            xci.write_text("{}")
            with patch("vivado_ip_test.plugins.common.testbench.load_metadata", return_value=(xci, {})):
                artifacts = plugin.generate_testbench(case)
            self.assertEqual(artifacts.input_path.read_text(), "\n" * 64)
            self.assertEqual(artifacts.expected_path.read_text(), "0\n" * 64)
            self.assertEqual(artifacts.metrics["checked_transaction_count"], 0)
            self.assertEqual(artifacts.metrics["checked_output_samples"], 64)
            self.assertEqual(artifacts.metrics["generated_count"], 1)
            text = artifacts.testbench_path.read_text()
            self.assertNotIn("variable stimulus", text)
            self.assertIn("unexpected data for inputless DUT", text)

    def test_block_design_metadata_preserves_and_checks_chunked_wide_constants(self):
        plugin, _ = plugin_case("xlconstant")
        value = (1 << 4095)+1
        spec = plugin.describe({"width": 4096, "value": str(value)})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            xci = root / spec.xci_glob.replace("*", "ip_test")
            xci.parent.mkdir(parents=True)
            instance = {"component_reference": "xilinx.com:ip:xlconstant:1.1", "parameters": {
                category: {k: [{"value": setting_text(v)}] for k, v in params.items()}
                for category, params in (("component_parameters", spec.settings), ("model_parameters", spec.model_parameters))},
                "boundary": {"ports": {"dout": [{"direction": "out", "size_left": "4095", "size_right": "0"}]}}}
            actual = hex(value)
            instance["parameters"]["model_parameters"]["CONST_VAL"][0]["value"] = [actual[:1000], actual[1000:]]
            xci.write_text(json.dumps({"ip_inst": instance}))
            self.assertEqual(load_metadata(root, spec, plugin.ip_name, plugin.version)[0], xci)
            instance["parameters"]["model_parameters"]["CONST_VAL"][0]["value"].reverse()
            xci.write_text(json.dumps({"ip_inst": instance}))
            with self.assertRaises(PluginError):
                load_metadata(root, spec, plugin.ip_name, plugin.version)

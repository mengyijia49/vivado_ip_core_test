from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class CicCompilerPluginTests(unittest.TestCase):
    def test_decimator_ports_settings_and_widths(self):
        plugin, case = plugin_case("cic_compiler")
        spec = plugin.describe(case.parameters)
        self.assertEqual([port.name for port in spec.inputs], [
            "aclk", "aresetn", "s_axis_data_tvalid", "m_axis_data_tready",
            "s_axis_data_tdata"])
        self.assertEqual([port.name for port in spec.outputs], [
            "s_axis_data_tready", "m_axis_data_tvalid", "m_axis_data_tdata",
            "event_halted"])
        self.assertEqual(spec.model_parameters["C_OUTPUT_WIDTH"], 12)
        self.assertEqual(spec.model_parameters["C_M_AXIS_DATA_TDATA_WIDTH"], 16)
        self.assertFalse(spec.preserves_transfer_count)

    def test_generation_records_different_input_and_output_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("cic_compiler", Path(directory))
            xci = Path(directory) / "fixture.xci"
            xci.write_text("{}")
            with patch("vivado_ip_test.plugins.common.stream.testbench.load_metadata",
                       return_value=(xci, {})):
                artifacts = plugin.generate_testbench(case)
            manifest = json.loads(artifacts.manifest_path.read_text())
            schedule = manifest["verification"]["schedule"]
            self.assertLess(schedule["checked_output_transfers"], artifacts.vector_count)
            required = Path(manifest["artifacts"]["required_inputs"]).read_text().splitlines()
            self.assertEqual(required[0], "1")
            text = artifacts.testbench_path.read_text()
            self.assertIn("output before accepted input", text)
            self.assertIn("event_halted => open", text)

    def test_invalid_parameters_are_rejected(self):
        plugin, case = plugin_case("cic_compiler")
        changes = ({"filter_type": "Lowpass"}, {"input_width": 1}, {"stages": 1},
                   {"differential_delay": 3}, {"rate": 3}, {"unknown": 1})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(PluginError):
                plugin.validate_case(replace(
                    case, parameters={**case.parameters, **change}))

    def test_all_extended_parameters_validate_without_vivado(self):
        root = Path(__file__).resolve().parents[4]
        plugin, _ = plugin_case("cic_compiler")
        cases = load_test_cases(root / "configs/ip/cic_compiler/extended.json")
        self.assertEqual(len(cases), 256)
        for case in cases:
            plugin.validate_case(case)

    def test_parameter_schema_is_referenced(self):
        root = Path(__file__).resolve().parents[4]
        schema = json.loads((root / "configs/schemas/ip_matrix.schema.json").read_text())
        rules = schema["$defs"]["case_fields"]["allOf"]
        refs = {rule["if"]["properties"]["ip_type"]["const"]:
                rule["then"]["properties"]["parameters"]["$ref"] for rule in rules}
        self.assertEqual(refs["cic_compiler"], "ip/cic_compiler/parameters.schema.json")

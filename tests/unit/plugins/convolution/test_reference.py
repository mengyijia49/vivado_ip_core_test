from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.convolution.reference import (
    convolution_codes, encoded_symbols, expected_transactions)
from vivado_ip_test.plugins.convolution.vectors import prepare_frames
from unit.plugins.cycle_helpers import plugin_case


class ConvolutionTests(unittest.TestCase):
    def test_literal_shift_register_example(self):
        self.assertEqual(encoded_symbols([1, 0, 1, 1], 3, (0b100, 0b011)),
                         [0b01, 0b10, 0b11, 0b11])

    def test_code_families_are_distinct_nonzero_and_fit(self):
        for length in range(3, 10):
            for rate in range(2, 8):
                families = [convolution_codes(length, rate, family)
                            for family in ("ascending", "descending", "spread")]
                for codes in families:
                    self.assertEqual(len(codes), rate)
                    self.assertEqual(len(set(codes)), rate)
                    self.assertTrue(all(0 < code < 1 << length for code in codes))
                self.assertEqual(len(set(families)), 3)

    def test_input_padding_is_ignored_and_output_padding_is_zero(self):
        parameters = {"constraint_length": 3, "output_rate": 2,
                      "code_family": "ascending"}
        low = expected_transactions([{"tdata": value} for value in (0, 1, 0, 1)], parameters)
        high = expected_transactions([{"tdata": value} for value in (0xFE, 0xFF, 0xAA, 0xAB)], parameters)
        self.assertEqual(low, high)
        self.assertTrue(all(frame["tdata"] < 4 for frame in low))

    def test_directed_prefix_exercises_state_and_padding(self):
        parameters = {"constraint_length": 7, "output_rate": 2,
                      "code_family": "spread"}
        frames = prepare_frames([{"tdata": 0x55}], parameters)
        bits = [frame["tdata"] & 1 for frame in frames[:-1]]
        self.assertIn([1] + [0] * 7, [bits[index:index + 8]
                                      for index in range(len(bits) - 7)])
        self.assertTrue(any(frame["tdata"] & 0xFE for frame in frames))
        self.assertEqual(frames[-1], {"tdata": 0x55})

    def test_ports_settings_and_model_codes(self):
        plugin, case = plugin_case("convolution")
        spec = plugin.describe(case.parameters)
        self.assertEqual([port.name for port in spec.inputs], [
            "aclk", "aresetn", "s_axis_data_tvalid", "m_axis_data_tready",
            "s_axis_data_tdata"])
        self.assertEqual([port.name for port in spec.outputs], [
            "s_axis_data_tready", "m_axis_data_tvalid", "m_axis_data_tdata"])
        self.assertEqual(spec.settings["Convolution_Code0"], "001")
        self.assertEqual(spec.model_parameters["C_CONVOLUTION_CODE1"], 2)

    def test_invalid_parameters_and_all_extended_cases(self):
        root = Path(__file__).resolve().parents[4]
        plugin, case = plugin_case("convolution")
        for change in ({"constraint_length": 2}, {"output_rate": 8},
                       {"code_family": "unknown"}, {"unknown": 1}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                plugin.validate_case(replace(case, parameters={**case.parameters, **change}))
        cases = load_test_cases(root / "configs/ip/convolution/extended.json")
        self.assertEqual(len(cases), 126)
        for extended_case in cases:
            plugin.validate_case(extended_case)

    def test_generation_records_codes_and_directed_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("convolution", Path(directory))
            xci = Path(directory) / "fixture.xci"
            xci.write_text("{}")
            with patch("vivado_ip_test.plugins.common.stream.testbench.load_metadata",
                       return_value=(xci, {})):
                artifacts = plugin.generate_testbench(case)
            manifest = json.loads(artifacts.manifest_path.read_text())
            contract = manifest["verification"]["schedule"]["reference_contract"]
            self.assertEqual(contract["convolution_codes"], [1, 2])
            self.assertGreater(manifest["verification"]["schedule"]
                               ["prepared_additional_transfers"], 0)
            self.assertIn("m_axis_data_tready", artifacts.testbench_path.read_text())

    def test_parameter_schema_is_referenced(self):
        root = Path(__file__).resolve().parents[4]
        schema = json.loads((root / "configs/schemas/ip_matrix.schema.json").read_text())
        rules = schema["$defs"]["case_fields"]["allOf"]
        refs = {rule["if"]["properties"]["ip_type"]["const"]:
                rule["then"]["properties"]["parameters"]["$ref"] for rule in rules}
        self.assertEqual(refs["convolution"],
                         "ip/convolution/parameters.schema.json")

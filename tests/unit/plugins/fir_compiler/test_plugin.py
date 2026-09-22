from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class FirPluginTests(unittest.TestCase):
    def test_ports_settings_and_full_precision_width(self):
        plugin, case = plugin_case("fir_compiler")
        spec = plugin.describe(case.parameters)
        self.assertEqual({port.name: port.width for port in spec.inputs}, {
            "aclk": 1, "aresetn": 1, "s_axis_data_tvalid": 1,
            "m_axis_data_tready": 1, "s_axis_data_tdata": 8})
        self.assertEqual({port.name: port.width for port in spec.outputs}, {
            "s_axis_data_tready": 1, "m_axis_data_tvalid": 1, "m_axis_data_tdata": 16})
        self.assertEqual(spec.settings["CoefficientVector"], "1,1,2")
        self.assertEqual(spec.settings["Output_Rounding_Mode"], "Full_Precision")
        self.assertEqual(spec.model_parameters["C_OUTPUT_WIDTH"], 10)

    def test_sidebands_and_wider_data_are_explicit(self):
        plugin, case = plugin_case("fir_compiler")
        parameters = {**case.parameters, "data_width": 16, "coefficient_width": 8,
                      "coefficients": [3, -5, 7], "has_last": True, "user_width": 7}
        spec = plugin.describe(parameters)
        self.assertEqual({port.name: port.width for port in spec.sink_payload},
                         {"tdata": 24, "tlast": 1, "tuser": 7})
        self.assertEqual(spec.settings["DATA_Has_TLAST"], "Packet_Framing")
        self.assertEqual(spec.model_parameters["C_OUTPUT_WIDTH"], 20)

    def test_invalid_parameters_are_rejected(self):
        plugin, case = plugin_case("fir_compiler")
        for changes in ({"coefficients": []}, {"coefficients": [0, 0]},
                        {"coefficients": [-9]}, {"coefficients": [1.5]},
                        {"architecture": "Transpose_Multiply_Accumulate", "coefficients": [1, 2, 1]},
                        {"data_width": 7}, {"user_width": 65}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                plugin.validate_case(replace(case, parameters={**case.parameters, **changes}))

    def test_generation_uses_stateful_reference_and_directed_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("fir_compiler", Path(directory))
            xci = Path(directory) / "fixture.xci"
            xci.write_text("{}")
            with patch("vivado_ip_test.plugins.common.stream.testbench.load_metadata", return_value=(xci, {})):
                result = plugin.generate_testbench(case)
            self.assertGreater(result.metrics["prepared_additional_transfers"], 0)
            self.assertEqual(result.metrics["reference_contract"]["model"], "integer_fir_convolution:1.0")
            self.assertNotEqual(result.input_path.read_bytes(), result.expected_path.read_bytes())

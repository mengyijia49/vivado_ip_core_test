from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class DdsCompilerPluginTests(unittest.TestCase):
    def test_phase_generator_ports_and_settings(self):
        plugin, case = plugin_case("dds_compiler")
        spec = plugin.describe(case.parameters)
        self.assertEqual({port.name: port.width for port in spec.inputs},
                         {"aresetn": 1, "m_axis_phase_tready": 1})
        self.assertEqual({port.name: port.width for port in spec.outputs},
                         {"m_axis_phase_tvalid": 1, "m_axis_phase_tdata": 8})
        self.assertEqual(spec.clock, "aclk")
        self.assertEqual(spec.settings["PINC1"], "00010001")
        self.assertEqual(spec.settings["Phase_offset"], "None")

    def test_fixed_offset_is_width_padded(self):
        plugin, case = plugin_case("dds_compiler")
        spec = plugin.describe({**case.parameters, "phase_offset": 37})
        self.assertEqual(spec.settings["POFF1"], "00100101")
        self.assertEqual(spec.settings["Phase_offset"], "Fixed")

    def test_invalid_values_are_rejected(self):
        plugin, case = plugin_case("dds_compiler")
        for changes in ({"phase_width": 2}, {"phase_width": 49},
                        {"phase_increment": 256}, {"phase_offset": 256},
                        {"phase_increment": -1}, {"unknown": 1}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                plugin.validate_case(replace(case, parameters={**case.parameters, **changes}))

    def test_generation_uses_stateful_sequence(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("dds_compiler", Path(directory))
            xci = Path(directory) / "fixture.xci"
            xci.write_text("{}")
            with patch("vivado_ip_test.plugins.common.testbench.load_metadata",
                       return_value=(xci, {})):
                result = plugin.generate_testbench(case)
            self.assertGreater(result.metrics["directed_sequence_cycles"], 40)
            self.assertGreater(result.metrics["reference_sequence_events"]["held_output_cycles"], 0)
            self.assertNotEqual(result.input_path.read_bytes(), result.expected_path.read_bytes())

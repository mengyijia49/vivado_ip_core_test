from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.configuration import load_test_cases
from unit.plugins.cycle_helpers import plugin_case


class ProcessorSystemResetPluginTests(unittest.TestCase):
    def test_ports_settings_and_output_widths(self):
        plugin, case = plugin_case("processor_system_reset")
        spec = plugin.describe(case.parameters)
        self.assertEqual([p.name for p in spec.inputs],
                         ["ext_reset_in", "aux_reset_in", "mb_debug_sys_rst", "dcm_locked"])
        self.assertEqual({p.name: p.width for p in spec.outputs},
                         {"mb_reset": 1, "bus_struct_reset": 1, "peripheral_reset": 1,
                          "interconnect_aresetn": 1, "peripheral_aresetn": 1})
        self.assertEqual(spec.clock, "slowest_sync_clk")
        self.assertEqual(spec.settings["C_EXT_RST_WIDTH"], 4)
        self.assertEqual(spec.settings["C_EXT_RESET_HIGH"], 1)

    def test_invalid_parameters_are_rejected(self):
        plugin, case = plugin_case("processor_system_reset")
        for changes in ({"ext_reset_width": 0}, {"aux_reset_width": 17},
                        {"bus_reset_count": 9}, {"peripheral_reset_count": 17},
                        {"ext_active_high": 1}, {"unknown": 1}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                plugin.validate_case(replace(case, parameters={**case.parameters, **changes}))

    def test_generation_contains_directed_state_sequence(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("processor_system_reset", Path(directory))
            xci = Path(directory) / "fixture.xci"
            xci.write_text("{}")
            with patch("vivado_ip_test.plugins.common.testbench.load_metadata",
                       return_value=(xci, {})):
                result = plugin.generate_testbench(case)
            self.assertGreater(result.metrics["directed_sequence_cycles"], 300)
            events = result.metrics["reference_sequence_events"]
            self.assertGreater(events["qualified_ext_resets"], 0)
            self.assertGreater(events["qualified_aux_resets"], 0)
            self.assertGreater(events["dcm_unlock_cycles"], 0)

    def test_parameter_schema_is_referenced_by_main_schema(self):
        root = Path(__file__).resolve().parents[4]
        schema = json.loads((root / "configs/schemas/ip_matrix.schema.json").read_text())
        rules = schema["$defs"]["case_fields"]["allOf"]
        refs = {rule["if"]["properties"]["ip_type"]["const"]:
                rule["then"]["properties"]["parameters"]["$ref"] for rule in rules}
        self.assertEqual(refs["processor_system_reset"],
                         "ip/processor_system_reset/parameters.schema.json")

    def test_all_extended_parameters_validate_without_vivado(self):
        root = Path(__file__).resolve().parents[4]
        plugin, _ = plugin_case("processor_system_reset")
        cases = load_test_cases(root / "configs/ip/processor_system_reset/extended.json")
        self.assertEqual(len(cases), 117)
        for case in cases:
            plugin.validate_case(case)

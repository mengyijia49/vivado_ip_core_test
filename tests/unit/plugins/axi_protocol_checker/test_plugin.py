from dataclasses import replace
from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.axi_protocol_checker.reference import expected_status
from vivado_ip_test.plugins.axi_protocol_checker.testbench import operation_calls
from vivado_ip_test.plugins.axi_protocol_checker.vectors import prepare_operations
from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class AxiProtocolCheckerTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axi_protocol_checker")

    def test_reference_maps_public_axi_checks_to_status_bits(self):
        self.assertEqual(expected_status("legal_read_write"), 0)
        self.assertEqual(expected_status("aw_reserved_burst"), 1 << 2)
        self.assertEqual(expected_status("ar_reserved_burst"), 1 << 39)
        self.assertEqual(expected_status("arvalid_dropped"), 1 << 56)

    def test_operations_always_include_legal_and_each_violation(self):
        operations = prepare_operations([], self.case.parameters)
        self.assertEqual(operations[0]["scenario"], "legal_read_write")
        self.assertEqual(len({item["scenario"] for item in operations}), 11)
        self.assertIn("run_case(10", operation_calls(operations, self.case.parameters))

    def test_1024_bit_bus_uses_encodable_fixed_burst_violations(self):
        parameters = {**self.case.parameters, "data_width": 1024}
        operations = prepare_operations([], parameters)
        self.assertEqual(operations[3]["scenario"], "aw_fixed_too_long")
        self.assertEqual(operations[8]["scenario"], "ar_fixed_too_long")
        self.assertEqual(expected_status("aw_fixed_too_long"), 1 << 5)

    def test_spec_matches_axi4_monitor_interface(self):
        spec = self.plugin.describe(self.case.parameters)
        self.assertEqual(spec.settings["PROTOCOL"], "AXI4")
        self.assertEqual(spec.settings["MESSAGE_LEVEL"], 0)
        self.assertEqual(spec.model_parameters["C_PC_STATUS_WIDTH"], 160)
        self.assertEqual({port.name for port in spec.outputs}, {"pc_status", "pc_asserted"})

    def test_invalid_parameters_are_rejected(self):
        self.plugin.validate_case(self.case)
        for change in ({"data_width": 48}, {"address_width": 48}, {"id_width": 2},
                       {"max_burst_length": 2}, {"max_outstanding": 4}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(
                    self.case, parameters={**self.case.parameters, **change}))

    def test_all_extended_parameters_validate_without_vivado(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/axi_protocol_checker/extended.json")
        self.assertEqual(len(cases), 10080)
        for case in cases:
            self.plugin.validate_case(case)


if __name__ == "__main__":
    unittest.main()

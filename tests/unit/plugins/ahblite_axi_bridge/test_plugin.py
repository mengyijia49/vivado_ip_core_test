from dataclasses import replace
from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.ahblite_axi_bridge.reference import (
    AhbLiteAxiReference,
    axi_attributes,
    write_strobe,
)
from vivado_ip_test.plugins.ahblite_axi_bridge.vectors import prepare_operations
from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class AhbLiteAxiBridgeTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("ahblite_axi_bridge")

    def test_reference_maps_protection_strobes_and_errors(self):
        self.assertEqual(axi_attributes(0b1010, False), (0b101, 0b10))
        self.assertEqual(axi_attributes(0b1010, True), (0b111, 0b10))
        self.assertEqual(write_strobe(0x103, 0, 32, True), 0b1000)
        self.assertEqual(write_strobe(0x102, 1, 32, True), 0b1100)
        self.assertEqual(write_strobe(0x102, 1, 32, False), 0b1111)
        operations = prepare_operations(self.case.parameters, self.case.verification)
        rows = AhbLiteAxiReference(self.case.parameters).expected(operations)
        self.assertEqual(len(rows), self.case.verification.case_budget)
        self.assertTrue(any(row["error"] for row in rows))

    def test_directed_operations_cover_sizes_lanes_reads_and_writes(self):
        operations = prepare_operations(self.case.parameters, self.case.verification)
        self.assertEqual({op["kind"] for op in operations}, {"read", "write"})
        self.assertEqual({op["size"] for op in operations}, {0, 1, 2})
        self.assertIn(3, {op["address"] % 4 for op in operations if op["size"] == 0})
        self.assertEqual({op["response"] for op in operations}, {0, 2, 3})

    def test_spec_has_ahb_and_all_axi_channels(self):
        spec = self.plugin.describe(self.case.parameters)
        self.assertEqual(spec.metadata.model_parameters["C_M_AXI_PROTOCOL"], "AXI4")
        names = {port.name for port in (*spec.metadata.inputs, *spec.metadata.outputs)}
        for name in ("s_ahb_htrans", "s_ahb_hready_out", "m_axi_awaddr",
                     "m_axi_wdata", "m_axi_bresp", "m_axi_araddr", "m_axi_rdata"):
            self.assertIn(name, names)

    def test_invalid_parameters_and_unsafe_timeout_are_rejected(self):
        self.plugin.validate_case(self.case)
        for change in ({"data_width": 48}, {"address_width": 48}, {"id_width": 2},
                       {"timeout_cycles": 16}, {"timeout_cycles": 32,
                        "stall_cycles": 7, "response_delay_cycles": 20}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(
                    self.case, parameters={**self.case.parameters, **change}))

    def test_all_extended_parameters_validate_without_vivado(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/ahblite_axi_bridge/extended.json")
        self.assertEqual(len(cases), 7680)
        for case in cases:
            self.plugin.validate_case(case)


if __name__ == "__main__":
    unittest.main()

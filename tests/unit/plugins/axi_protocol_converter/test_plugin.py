from dataclasses import replace
from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.axi_protocol_converter.reference import (
    AxiProtocolConverterReference, BURSTS, burst_addresses,
)
from vivado_ip_test.plugins.axi_protocol_converter.testbench import operation_calls
from vivado_ip_test.plugins.axi_protocol_converter.vectors import prepare_operations
from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class AxiProtocolConverterTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axi_protocol_converter")

    def test_burst_addresses_cover_fixed_increment_and_wrap(self):
        self.assertEqual(burst_addresses(0x10C, 4, 2, BURSTS["Fixed"], 32), [0x10C] * 4)
        self.assertEqual(burst_addresses(0x10C, 4, 2, BURSTS["Increment"], 32),
                         [0x10C, 0x110, 0x114, 0x118])
        self.assertEqual(burst_addresses(0x10C, 4, 2, BURSTS["Wrap"], 32),
                         [0x10C, 0x100, 0x104, 0x108])

    def test_reference_splits_bursts_and_restores_ids(self):
        operations = prepare_operations([], self.case.parameters)
        model = AxiProtocolConverterReference(self.case.parameters)
        accesses, outputs = model.evaluate(operations)
        self.assertGreater(len(accesses), len(operations))
        self.assertTrue(any(row["response"] == 2 for row in outputs))
        self.assertTrue(any(row["response"] == 3 for row in outputs))
        self.assertTrue(all("id" in row for row in outputs))

    def test_spec_is_axi4_to_axilite_conversion(self):
        spec = self.plugin.describe(self.case.parameters)
        self.assertEqual(spec.settings["SI_PROTOCOL"], "AXI4")
        self.assertEqual(spec.settings["MI_PROTOCOL"], "AXI4LITE")
        self.assertEqual(spec.settings["TRANSLATION_MODE"], 2)
        self.assertEqual(spec.model_parameters["C_AXI_SUPPORTS_USER_SIGNALS"], 0)

    def test_wide_id_is_rendered_as_bits_not_vhdl_integer(self):
        parameters = {**self.case.parameters, "id_width": 32}
        operation = prepare_operations([], parameters)[0]
        operation["id"] = (1 << 32) - 1
        rendered = operation_calls([operation], parameters)
        self.assertIn('"11111111111111111111111111111111"', rendered)
        self.assertNotIn("4294967295", rendered)

    def test_invalid_parameters_are_rejected(self):
        self.plugin.validate_case(self.case)
        for change in ({"data_width": 48}, {"address_width": 16}, {"id_width": 2},
                       {"burst_length": 3}, {"downstream_stall_cycles": 3}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(
                    self.case, parameters={**self.case.parameters, **change}))

    def test_all_extended_parameters_validate_without_vivado(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/axi_protocol_converter/extended.json")
        self.assertEqual(len(cases), 600)
        for case in cases:
            self.plugin.validate_case(case)


if __name__ == "__main__":
    unittest.main()

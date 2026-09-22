from dataclasses import replace
from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.axi_memory_init.reference import AxiMemoryInitReference, initial_value
from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class AxiMemoryInitTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axi_memory_init")

    def test_reference_calculates_full_bursts_and_patterns(self):
        model = AxiMemoryInitReference(self.case.parameters)
        self.assertEqual(model.beat_count, 512)
        self.assertEqual(model.burst_count, 32)
        self.assertEqual(model.burst_addresses()[:2], [0, 64])
        self.assertEqual(model.output_rows()[15], (0, 15, 1))
        self.assertEqual(initial_value("EdgeBits", 32), 0x80000001)
        self.assertEqual(initial_value("Alternating", 64), 0xA5A5A5A5A5A5A5A5)

    def test_spec_has_full_axi4_read_write_interface(self):
        spec = self.plugin.describe(self.case.parameters)
        self.assertEqual(spec.settings["READ_WRITE_MODE"], "READ_WRITE")
        self.assertEqual(spec.metadata.model_parameters["C_PROTOCOL"], 0)
        self.assertEqual(spec.metadata.model_parameters["C_BASE_ADDR"], "0x0")
        names = {port.name for port in (*spec.metadata.inputs, *spec.metadata.outputs)}
        for name in ("m_axi_awaddr", "m_axi_wdata", "m_axi_bresp",
                     "m_axi_araddr", "m_axi_rdata", "init_complete_out", "aclken"):
            self.assertIn(name, names)

    def test_alignment_width_and_catalog_values_are_checked(self):
        self.plugin.validate_case(self.case)
        for change in ({"data_width": 48}, {"base_address": 1},
                       {"address_size": 10}, {"stall_cycles": 2}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(
                    self.case, parameters={**self.case.parameters, **change}))

    def test_all_extended_parameters_validate_without_vivado(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/axi_memory_init/extended.json")
        self.assertEqual(len(cases), 46080)
        for case in cases:
            self.plugin.validate_case(case)


if __name__ == "__main__":
    unittest.main()

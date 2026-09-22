from dataclasses import replace
import unittest

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.axi_bram_controller.reference import AxiBramModel, merge_bytes
from unit.plugins.cycle_helpers import plugin_case


class AxiBramControllerTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axi_bram_controller")
        self.p = {"depth": 1024, "single_port": True}

    @staticmethod
    def command(action, address=0, data=0, strobe=0, awprot=0, arprot=0):
        return {"action": int(action), "address": address, "data": data,
                "strobe": strobe, "s_axi_awprot": awprot, "s_axi_arprot": arprot}

    def test_byte_strobes_update_only_selected_lanes(self):
        self.assertEqual(merge_bytes(0x11223344, 0xAABBCCDD, 0b0101), 0x11BB33DD)
        model = AxiBramModel(self.p)
        model.step(self.command(Action.WRITE, 0, 0x11223344, 15))
        model.step(self.command(Action.WRITE, 0, 0xAABBCCDD, 5))
        self.assertEqual(model.step(self.command(Action.READ, 0))["read_data"], 0x11BB33DD)

    def test_addresses_are_independent_and_reset_preserves_memory(self):
        model = AxiBramModel(self.p)
        model.step(self.command(Action.WRITE, 0, 0x12345678, 15))
        model.step(self.command(Action.WRITE, 4092, 0x89ABCDEF, 15))
        model.step(self.command(Action.RESET))
        self.assertEqual(model.read(0), 0x12345678)
        self.assertEqual(model.read(4), 0)
        self.assertEqual(model.read(4092), 0x89ABCDEF)

    def test_zero_strobe_does_not_change_memory(self):
        model = AxiBramModel(self.p)
        model.write(8, 0xFFFFFFFF, 0)
        self.assertEqual(model.read(8), 0)
        self.assertEqual(model.memory, {})

    def test_spec_matches_lite_internal_memory_interface(self):
        spec = self.plugin.describe(self.p)
        self.assertEqual(spec.address_width, 12)
        self.assertEqual(spec.settings["PROTOCOL"], "AXI4LITE")
        self.assertEqual(spec.settings["BMG_INSTANCE"], "INTERNAL")
        self.assertEqual([p.name for p in spec.side_inputs], ["s_axi_awprot", "s_axi_arprot"])
        self.assertEqual(spec.side_outputs, ())

    def test_depth_controls_address_width(self):
        self.assertEqual(self.plugin.describe({**self.p, "depth": 262144}).address_width, 20)

    def test_invalid_parameters_are_rejected(self):
        for changes in ({"depth": 512}, {"depth": 3072}, {"depth": True},
                        {"single_port": 1}, {"extra": 1}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                self.plugin.describe({**self.p, **changes})

    def test_sequence_covers_strobes_protection_boundaries_and_persistence(self):
        spec = self.plugin.describe(self.p)
        rows = [{"sample_word": 1023, "sample_data": 0xDEADBEEF,
                 "sample_strobe": 9, "s_axi_awprot": 7, "s_axi_arprot": 6}]
        sequence = spec.prepare_operations(rows)
        writes = [op["command"] for op in sequence if op["command"]["action"] == Action.WRITE]
        reads = [op["command"] for op in sequence if op["command"]["action"] == Action.READ]
        self.assertEqual({row["strobe"] for row in writes}, set(range(16)))
        self.assertTrue(any(row["address"] == 4092 for row in writes))
        self.assertTrue(any(row["s_axi_awprot"] == 7 for row in writes))
        self.assertTrue(any(row["s_axi_arprot"] == 6 for row in reads))
        phases = [op["phase"] for op in sequence]
        self.assertIn("reset_persistence", phases)
        self.assertEqual(phases[-1], "reset_suffix")

    def test_case_validation_accepts_shipped_case_and_rejects_wrong_identity(self):
        self.plugin.validate_case(self.case)
        with self.assertRaises(PluginError):
            self.plugin.validate_case(replace(self.case, ip_name="wrong"))


if __name__ == "__main__":
    unittest.main()

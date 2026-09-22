from dataclasses import replace
import unittest

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.lmb_bram_controller.reference import (
    LmbBramControllerModel, address_mask, protection_allowed)
from unit.plugins.cycle_helpers import plugin_case


class LmbBramControllerTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("lmb_bram_controller")
        self.p = {"data_width": 32, "address_width": 32, "base_address": 0,
                  "address_size": 4096, "write_access": "All_Writes",
                  "protection": False, "protection_mask": 255}

    def frame(self, **changes):
        frame = self.plugin.describe(self.p).frame()
        frame.update(changes)
        return frame

    def test_mask_and_protection_bit_order(self):
        self.assertEqual(address_mask(4096), 0xFFFFFFFFFFFFF000)
        self.assertTrue(protection_allowed(0x80, 0, False))
        self.assertFalse(protection_allowed(0x80, 1, False))
        self.assertTrue(protection_allowed(0x08, 0, True))

    def test_selected_write_forwards_bram_signals_and_byte_enables(self):
        model = LmbBramControllerModel(self.p)
        result = model.step(self.frame(LMB_ABus=0xFFC, LMB_WriteDBus=0x89ABCDEF,
            LMB_AddrStrobe=1, LMB_WriteStrobe=1, LMB_BE=5, BRAM_Din_A=0x12345678))
        self.assertEqual(result["BRAM_Addr_A"], 0xFFC)
        self.assertEqual(result["BRAM_Dout_A"], 0x89ABCDEF)
        self.assertEqual(result["BRAM_WEN_A"], 5)
        self.assertEqual(result["Sl_DBus"], 0x12345678)
        self.assertEqual(result["Sl_Ready"], 1)

    def test_outside_address_is_not_acknowledged_or_written(self):
        model = LmbBramControllerModel(self.p)
        result = model.step(self.frame(LMB_ABus=0x1000, LMB_AddrStrobe=1,
                                       LMB_WriteStrobe=1, LMB_BE=15))
        self.assertEqual(result["Sl_Ready"], 0)
        self.assertEqual(result["BRAM_WEN_A"], 0)
        self.assertEqual(result["BRAM_EN_A"], 1)

    def test_reset_suppresses_response_but_not_combinational_bram_enable(self):
        model = LmbBramControllerModel(self.p)
        result = model.step(self.frame(LMB_Rst=1, LMB_AddrStrobe=1, LMB_ReadStrobe=1))
        self.assertEqual(result["Sl_Ready"], 0)
        self.assertEqual(result["BRAM_EN_A"], 1)

    def test_write_access_modes(self):
        for mode, expected in (("Read_Only", 0), ("Word_Only", 15), ("All_Writes", 5)):
            model = LmbBramControllerModel({**self.p, "write_access": mode})
            result = model.step(self.frame(LMB_AddrStrobe=1, LMB_WriteStrobe=1, LMB_BE=5))
            self.assertEqual(result["BRAM_WEN_A"], expected)

    def test_spec_ports_follow_width_and_protection(self):
        spec = self.plugin.describe({**self.p, "data_width": 64, "address_width": 64,
                                     "protection": True, "protection_mask": 105})
        self.assertIn("LMB_Prot", [port.name for port in spec.inputs])
        self.assertEqual(next(p.width for p in spec.inputs if p.name == "LMB_BE"), 8)
        self.assertEqual(spec.settings["C_MASK"], "0xFFFFFFFFFFFFF000")

    def test_invalid_parameters_are_rejected(self):
        for changes in ({"data_width": 16}, {"address_size": 8192},
                        {"base_address": 1}, {"base_address": 1 << 32},
                        {"protection_mask": 1}, {"extra": 1}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                self.plugin.describe({**self.p, **changes})

    def test_directed_sequence_covers_byte_enables_decode_reset_and_conflicts(self):
        spec = self.plugin.describe(self.p)
        sequence = list(spec.prefix())
        self.assertEqual({row["LMB_BE"] for row in sequence if row["LMB_WriteStrobe"]}, set(range(16)))
        self.assertTrue(any(row["LMB_ABus"] == 4096 for row in sequence))
        self.assertTrue(any(row["LMB_Rst"] for row in sequence))
        self.assertTrue(any(row["LMB_ReadStrobe"] and row["LMB_WriteStrobe"] for row in sequence))

    def test_case_validation_accepts_shipped_case_and_rejects_wrong_identity(self):
        self.plugin.validate_case(self.case)
        with self.assertRaises(PluginError):
            self.plugin.validate_case(replace(self.case, ip_name="wrong"))


if __name__ == "__main__":
    unittest.main()

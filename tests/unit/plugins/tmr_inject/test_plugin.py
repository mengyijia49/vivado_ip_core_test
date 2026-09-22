from dataclasses import replace
from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.tmr_inject.reference import TmrInjectModel
from unit.plugins.cycle_helpers import plugin_case


class TmrInjectTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("tmr_inject")
        self.p = dict(self.case.parameters)

    def frame(self, **changes):
        frame = self.plugin.describe(self.p).frame()
        frame.update(changes)
        return frame

    def test_model_injects_once_and_forwards_lmb(self):
        model = TmrInjectModel(self.p)
        base = self.p["base_address"]
        enable = self.p["magic"] | (self.p["cpu_id"] << 8) | 1 << 10
        for address, data in ((base + 4, 0x100), (base + 8, 0xDEADBEEF),
                              (base, enable)):
            model.step(self.frame(LMB_ABus=address, LMB_WriteDBus=data,
                                   LMB_AddrStrobe=1, LMB_WriteStrobe=1))
            model.step(self.frame())
        hit = model.step(self.frame(MB_LMB_ABus=0x103, MB_LMB_AddrStrobe=1,
                                    BRAM_Sl_DBus=0x12345678, BRAM_Sl_Ready=1))
        self.assertEqual(hit["MB_Sl_DBus"], 0xDEADBEEF)
        self.assertEqual(hit["BRAM_LMB_ABus"], 0x103)
        model.step(self.frame(BRAM_Sl_Ready=1))
        second = model.step(self.frame(MB_LMB_ABus=0x100, MB_LMB_AddrStrobe=1,
                                       BRAM_Sl_DBus=0x12345678))
        self.assertEqual(second["MB_Sl_DBus"], 0x12345678)

    def test_wrong_magic_and_cpu_do_not_arm(self):
        model = TmrInjectModel(self.p)
        base = self.p["base_address"]
        for value in (1 << 10, self.p["magic"] | (3 << 8) | (1 << 10)):
            model.step(self.frame(LMB_ABus=base, LMB_WriteDBus=value,
                                  LMB_AddrStrobe=1, LMB_WriteStrobe=1))
            model.step(self.frame())
        self.assertEqual(model.event_counts["injection_armed"], 0)
        self.assertEqual(model.event_counts["invalid_arm_writes"], 2)

    def test_invalid_control_write_has_priority_over_injection_clear(self):
        model = TmrInjectModel(self.p)
        base = self.p["base_address"]
        enable = self.p["magic"] | (self.p["cpu_id"] << 8) | 1 << 10
        for address, data in ((base + 4, 0x100), (base, enable)):
            model.step(self.frame(LMB_ABus=address, LMB_WriteDBus=data,
                                  LMB_AddrStrobe=1, LMB_WriteStrobe=1))
            model.step(self.frame())

        model.step(self.frame(
            MB_LMB_ABus=0x100, MB_LMB_AddrStrobe=1,
            LMB_ABus=base, LMB_WriteDBus=0,
            LMB_AddrStrobe=1, LMB_WriteStrobe=1,
        ))
        model.step(self.frame(BRAM_Sl_Ready=1))

        self.assertTrue(model.enabled)
        self.assertFalse(model.injecting)
        second = model.step(self.frame(MB_LMB_ABus=0x100, MB_LMB_AddrStrobe=1))
        self.assertEqual(second["MB_Sl_DBus"], model.instruction)

    def test_directed_sequence_covers_arm_fault_and_transparency(self):
        spec = self.plugin.describe(self.p)
        model = spec.model_factory()
        rows = list(spec.prefix())
        for row in rows:
            model.step(row)
        self.assertGreater(model.event_counts["faults_injected"], 0)
        self.assertGreater(model.event_counts["invalid_arm_writes"], 0)
        self.assertTrue(any(row["BRAM_Sl_Wait"] for row in rows))
        self.assertTrue(any(row["MB_LMB_WriteStrobe"] for row in rows))

    def test_protection_ports_and_denied_write(self):
        parameters = {**self.p, "protection": True, "protection_mask": 0x69}
        spec = self.plugin.describe(parameters)
        self.assertIn("LMB_Prot", {port.name for port in spec.inputs})
        self.assertIn("MB_LMB_Prot", {port.name for port in spec.inputs})
        self.assertIn("BRAM_LMB_Prot", {port.name for port in spec.outputs})
        model = spec.model_factory()
        for row in spec.prefix():
            model.step(row)
        self.assertGreater(model.event_counts["protected_writes_rejected"], 0)

    def test_invalid_parameters_are_rejected(self):
        for changes in ({"cpu_id": 0}, {"magic": 256}, {"address_size": 8192},
                        {"base_address": 1}, {"protection_mask": 1}, {"extra": 1}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(
                    self.case, parameters={**self.p, **changes}))

    def test_extended_matrix_has_unique_valid_parameters(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/tmr_inject/extended.json")
        self.assertEqual(len(cases), 675)
        seen = set()
        for case in cases:
            self.plugin.validate_case(case)
            key = tuple(sorted(case.parameters.items()))
            self.assertNotIn(key, seen)
            seen.add(key)

    def test_identity_is_checked(self):
        self.plugin.validate_case(self.case)
        with self.assertRaises(PluginError):
            self.plugin.validate_case(replace(self.case, ip_name="wrong"))


if __name__ == "__main__":
    unittest.main()

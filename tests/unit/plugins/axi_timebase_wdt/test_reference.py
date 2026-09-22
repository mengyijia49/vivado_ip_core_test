from dataclasses import replace
import unittest

from vivado_ip_test.plugins.axi_timebase_wdt.reference import AxiTimebaseWdtModel, EWDT1, WDS, WRS
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.axilite.spec import Action
from unit.plugins.cycle_helpers import plugin_case


class AxiTimebaseWdtTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axi_timebase_wdt")
        self.p = {"interval": 8, "enable_once": True}

    @staticmethod
    def command(action, address=0, data=0, strobe=0, cycles=0):
        return {"action": int(action), "address": address, "data": data,
                "strobe": strobe, "freeze": 1, "run_cycles": cycles}

    def test_first_expiration_interrupts_and_second_resets(self):
        model = AxiTimebaseWdtModel(self.p)
        model.step(self.command(Action.WRITE, 0, EWDT1, 15))
        model.step(self.command(Action.WINDOW, cycles=256))
        self.assertEqual(model.wds, True)
        self.assertEqual(model.reset_asserted, False)
        model.step(self.command(Action.WINDOW, cycles=256))
        self.assertEqual(model.wds, True)
        self.assertEqual(model.reset_asserted, True)
        self.assertEqual(model.reset_status, True)

    def test_clear_state_restarts_two_expiration_sequence(self):
        model = AxiTimebaseWdtModel(self.p)
        model.write(0, EWDT1)
        model.advance(256)
        model.write(0, EWDT1 | WDS)
        model.advance(256)
        self.assertTrue(model.wds)
        self.assertFalse(model.reset_asserted)

    def test_enable_once_and_repeated_modes_differ(self):
        for once, enabled in ((True, True), (False, False)):
            model = AxiTimebaseWdtModel({**self.p, "enable_once": once})
            model.write(0, EWDT1)
            model.write(0, 0)
            self.assertEqual(model.enabled, enabled)

    def test_reset_status_survives_reset_until_software_clear(self):
        model = AxiTimebaseWdtModel(self.p)
        model.reset_status = True
        model.step(self.command(Action.RESET))
        self.assertTrue(model.reset_status)
        model.write(0, WRS)
        self.assertFalse(model.reset_status)

    def test_runtime_width_changes_period_and_tbr_readback(self):
        model = AxiTimebaseWdtModel(self.p)
        model.write(12, 10)
        model.write(4, 1)
        model.advance(1023)
        self.assertFalse(model.wds)
        model.advance(1)
        self.assertTrue(model.wds)
        self.assertEqual(model.read(8), 1024)
        self.assertEqual(model.read(12), 10)

    def test_timebase_keeps_running_while_watchdog_is_disabled(self):
        model = AxiTimebaseWdtModel({**self.p, "enable_once": False})
        model.advance(37)
        self.assertEqual(model.read(8), 37)
        self.assertFalse(model.wds)

    def test_spec_is_legacy_axilite_with_freeze_window(self):
        spec = self.plugin.describe(self.p)
        self.assertEqual(spec.address_width, 4)
        self.assertEqual(spec.window.control, "freeze")
        self.assertEqual(spec.settings["ENABLE_WINDOW_WDT"], 0)
        self.assertEqual(spec.model_parameters["C_WDT_ENABLE_ONCE"], 1)

    def test_sequence_checks_strobes_expirations_disable_and_runtime_width(self):
        spec = self.plugin.describe(self.p)
        operations = spec.prepare_operations([{"sample_cycles": 255}])
        phases = {op["phase"] for op in operations}
        self.assertIn("clear_and_second_expiration", phases)
        self.assertIn("enable_behavior", phases)
        self.assertIn("second_enable_and_runtime_width", phases)
        strobes = {op["command"]["strobe"] for op in operations
                   if op["command"]["action"] == Action.WRITE}
        self.assertTrue(set(range(9)).issubset(strobes))

    def test_invalid_parameters_and_identity_are_rejected(self):
        for p in ({"interval": 7, "enable_once": True}, {"interval": 16, "enable_once": True},
                  {"interval": 8, "enable_once": 1}, {"interval": 8, "enable_once": True, "x": 1}):
            with self.subTest(p=p), self.assertRaises(PluginError):
                self.plugin.describe(p)
        with self.assertRaises(PluginError):
            self.plugin.validate_case(replace(self.case, ip_name="wrong"))


if __name__ == "__main__":
    unittest.main()

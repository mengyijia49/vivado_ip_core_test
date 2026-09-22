from dataclasses import replace
import unittest

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.util_ff.reference import UtilFfModel, parse_init
from unit.plugins.cycle_helpers import plugin_case


class UtilFfTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("util_ff")

    def test_fdre_init_enable_reset_and_data(self):
        model = UtilFfModel(self.case.parameters)
        self.assertEqual(model.step({"D": 0, "reset": 0, "clk_enable": 0}), {"Q": 0xA5})
        self.assertEqual(model.step({"D": 0x36, "reset": 0, "clk_enable": 1}), {"Q": 0x36})
        self.assertEqual(model.step({"D": 0xFF, "reset": 0, "clk_enable": 0}), {"Q": 0x36})
        self.assertEqual(model.step({"D": 0xFF, "reset": 1, "clk_enable": 0}), {"Q": 0})

    def test_active_low_clear_and_inverted_data(self):
        p = {"width": 4, "ff_type": "FDCE", "init_value": "0x3",
             "control_active_high": False, "data_inverted": True, "gate_active_high": True}
        model = UtilFfModel(p)
        self.assertEqual(model.step({"D": 0x3, "clear": 1, "clk_enable": 1}), {"Q": 0xC})
        self.assertEqual(model.step({"D": 0xF, "clear": 0, "clk_enable": 0}), {"Q": 0})

    def test_latch_gate_hold_and_asynchronous_preset(self):
        p = {"width": 3, "ff_type": "LDPE", "init_value": "0x2",
             "control_active_high": True, "data_inverted": False, "gate_active_high": False}
        model = UtilFfModel(p)
        self.assertEqual(model.step({"D": 5, "preset": 0, "gate_enable": 1, "G": 0}), {"Q": 5})
        self.assertEqual(model.step({"D": 1, "preset": 0, "gate_enable": 1, "G": 1}), {"Q": 5})
        self.assertEqual(model.step({"D": 0, "preset": 1, "gate_enable": 0, "G": 1}), {"Q": 7})

    def test_ports_follow_selected_primitive(self):
        ff = self.plugin.describe(self.case.parameters)
        self.assertEqual([p.name for p in ff.inputs], ["D", "reset", "clk_enable"])
        self.assertEqual(ff.clock, "clk")
        latch = self.plugin.describe({**self.case.parameters, "ff_type": "LDCE",
            "data_inverted": False, "gate_active_high": False})
        self.assertEqual([p.name for p in latch.inputs], ["D", "clear", "gate_enable", "G"])
        self.assertIsNone(latch.clock)

    def test_active_low_control_starts_inactive(self):
        spec = self.plugin.describe({**self.case.parameters, "ff_type": "FDPE",
                                     "control_active_high": False})
        self.assertEqual(spec.initial_values, {"preset": 1})

    def test_invalid_parameters_are_rejected(self):
        self.plugin.validate_case(self.case)
        for parameters in (
            {**self.case.parameters, "width": 0},
            {**self.case.parameters, "ff_type": "DFF"},
            {**self.case.parameters, "init_value": "A5"},
            {**self.case.parameters, "init_value": "0x100"},
            {**self.case.parameters, "ff_type": "LDCE", "data_inverted": True},
        ):
            with self.subTest(parameters=parameters), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(self.case, parameters=parameters))
        with self.assertRaises(PluginError):
            parse_init("0x100", 8)


if __name__ == "__main__":
    unittest.main()

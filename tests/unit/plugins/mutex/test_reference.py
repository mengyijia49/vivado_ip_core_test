from dataclasses import replace
import unittest

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.mutex.reference import MutexModel, MutexPlan
from unit.plugins.cycle_helpers import plugin_case


class MutexTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("mutex")

    def test_owner_controls_updates_without_hardware_protection(self):
        model = MutexModel(2, 1, False, False)
        model.write_mutex(0, 0, 0x25)
        model.write_mutex(1, 0, 0x69)
        self.assertEqual(model.read_mutex(1, 0), 0x25)
        model.write_mutex(1, 0, 0x24)
        self.assertEqual(model.read_mutex(0, 0), 0)

    def test_hardware_protection_includes_interface_identity(self):
        model = MutexModel(4, 2, True, True)
        model.write_mutex(0, 0, 0x25)
        model.write_mutex(1, 0, 0x24)
        self.assertEqual(model.read_mutex(1, 0), 0x25)
        model.write_mutex(0, 0, 0x24)
        self.assertEqual(model.read_mutex(1, 0), 0)
        model.write_user(3, 1, 0xA55A3CC3)
        self.assertEqual(model.read_user(0, 1), 0xA55A3CC3)

    def test_simultaneous_access_uses_lowest_interface(self):
        model = MutexModel(4, 1, False, True)
        model.simultaneous_acquire(0, [3, 5, 7, 9])
        self.assertEqual(model.read_mutex(3, 0), 3)
        with self.assertRaises(PluginError):
            model.simultaneous_acquire(0, [3])

    def test_multi_mutex_storage_requires_explicit_initialization_after_reset(self):
        single = MutexModel(2, 1, True, False)
        single.write_mutex(0, 0, 0x25); single.write_user(0, 0, 7); single.reset()
        self.assertEqual((single.read_mutex(0, 0), single.read_user(0, 0)), (0, 0))
        multiple = MutexModel(2, 2, True, False)
        multiple.write_mutex(0, 0, 0x25); multiple.write_user(0, 0, 7); multiple.reset()
        self.assertEqual((multiple.read_mutex(0, 0), multiple.read_user(0, 0)), (0x25, 7))

    def test_plan_and_metadata_match_catalog(self):
        plan = MutexPlan.from_parameters(self.case.parameters)
        spec = self.plugin._backend.metadata_spec(plan)
        self.assertEqual(spec.settings["C_NUM_AXI"], 2)
        self.assertEqual(spec.settings["C_ASYNC_CLKS"], 0)
        self.assertEqual(spec.clock, "S0_AXI_ACLK")
        self.assertEqual(spec.clock_aliases, ("S1_AXI_ACLK",))
        self.assertEqual(len(spec.inputs), 20)
        self.assertEqual(len(spec.outputs), 16)

    def test_validation_rejects_unsupported_scope(self):
        self.plugin.validate_case(self.case)
        for parameters in (
            {**self.case.parameters, "num_interfaces": 3},
            {**self.case.parameters, "num_mutexes": 0},
            {**self.case.parameters, "enable_user": 1},
        ):
            with self.subTest(parameters=parameters), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(self.case, parameters=parameters))
        with self.assertRaises(PluginError):
            self.plugin.validate_case(replace(
                self.case, verification=replace(self.case.verification, case_budget=2)))


if __name__ == "__main__":
    unittest.main()

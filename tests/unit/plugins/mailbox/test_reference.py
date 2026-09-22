from dataclasses import replace
from pathlib import Path
import unittest

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.mailbox.reference import (
    AxisMailboxModel, AxisMailboxPlan, MailboxModel, MailboxPlan,
)
from unit.plugins.cycle_helpers import plugin_case


class MailboxTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("mailbox")

    def test_bidirectional_queues_preserve_order(self):
        model = MailboxModel(16, False)
        model.write_data(0, 0x12345678)
        model.write_data(0, 0xFFFFFFFFF)
        model.write_data(1, 0xA5A55A5A)
        self.assertEqual(model.read_data(1), (0, 0x12345678))
        self.assertEqual(model.read_data(1), (0, 0xFFFFFFFF))
        self.assertEqual(model.read_data(0), (0, 0xA5A55A5A))

    def test_full_and_empty_errors_are_read_to_clear(self):
        model = MailboxModel(2, True)
        self.assertEqual(model.read_data(0), (2, None))
        self.assertEqual(model.read_errors(0), 1)
        self.assertEqual(model.read_errors(0), 0)
        self.assertEqual([model.write_data(0, value) for value in range(3)], [0, 0, 2])
        self.assertEqual(model.read_errors(0), 2)

    def test_status_thresholds_and_clear_operations(self):
        model = MailboxModel(4, False)
        model.send_threshold[0] = 1
        model.receive_threshold[1] = 1
        self.assertEqual(model.status(0), 5)
        model.write_data(0, 1)
        model.write_data(0, 2)
        self.assertEqual(model.status(0), 1)
        self.assertEqual(model.status(1), 12)
        model.clear_receive(1)
        self.assertEqual(model.status(1), 5)
        model.write_data(1, 3)
        model.clear_send(1)
        self.assertEqual(model.status(1), 5)

    def test_reset_discards_data_errors_and_thresholds(self):
        model = MailboxModel(2, False)
        model.write_data(0, 1)
        model.read_data(0)
        model.send_threshold[0] = 7
        model.receive_threshold[1] = 7
        model.reset()
        self.assertEqual((model.status(0), model.status(1)), (5, 5))
        self.assertEqual((model.read_errors(0), model.read_errors(1)), (0, 0))

    def test_plan_and_metadata_match_dual_axi_catalog(self):
        plan = MailboxPlan.from_parameters(self.case.parameters)
        spec = self.plugin._backend.metadata_spec(plan)
        self.assertEqual(spec.settings["C_INTERCONNECT_PORT_0"], 2)
        self.assertEqual(spec.clock, "S0_AXI_ACLK")
        self.assertEqual(spec.clock_aliases, ("S1_AXI_ACLK",))
        self.assertEqual(len(spec.inputs), 20)
        self.assertEqual(len(spec.outputs), 18)

    def test_validation_rejects_unsupported_parameters(self):
        self.plugin.validate_case(self.case)
        for parameters in (
            {**self.case.parameters, "depth": 24},
            {**self.case.parameters, "depth": 8},
            {**self.case.parameters, "memory_style": "Ultra_RAM"},
            {**self.case.parameters, "enable_bus_error": 1},
        ):
            with self.subTest(parameters=parameters), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(self.case, parameters=parameters))
        with self.assertRaises(PluginError):
            self.plugin.validate_case(replace(
                self.case, verification=replace(self.case.verification, case_budget=2)))

    def test_axis_model_routes_to_opposite_side_and_preserves_last(self):
        model = AxisMailboxModel(2)
        self.assertTrue(model.push(0, 0x1FFFFFFFF, False))
        self.assertTrue(model.push(0, 2, True))
        self.assertFalse(model.push(0, 3, False))
        self.assertEqual(model.pop(1).data, 0xFFFFFFFF)
        self.assertTrue(model.pop(1).last)
        self.assertIsNone(model.pop(0))
        model.push(1, 4, True)
        model.reset()
        self.assertIsNone(model.pop(0))

    def test_axis_plan_metadata_and_expected_cross_routing(self):
        root = Path(__file__).resolve().parents[4]
        axis_case = next(case for case in load_test_cases(
            root / "configs/ip/mailbox/regression.json")
                         if case.parameters["interface_mode"] == "Axis")
        plan = AxisMailboxPlan.from_parameters(axis_case.parameters)
        outputs = plan.expected_outputs()
        self.assertEqual(outputs[0], plan.input_sequences()[1])
        self.assertEqual(outputs[1], plan.input_sequences()[0])
        spec = self.plugin._backend.metadata_spec(plan)
        self.assertEqual(spec.settings["C_INTERCONNECT_PORT_0"], 4)
        self.assertEqual(spec.clock_aliases,
                         ("M0_AXIS_ACLK", "S1_AXIS_ACLK", "M1_AXIS_ACLK"))
        self.assertEqual(len(spec.inputs), 9)
        self.assertEqual(len(spec.outputs), 10)
        self.plugin.validate_case(axis_case)


if __name__ == "__main__":
    unittest.main()

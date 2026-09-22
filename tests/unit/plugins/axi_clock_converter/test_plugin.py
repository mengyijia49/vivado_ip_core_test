from dataclasses import replace
from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.axi_clock_converter.reference import (
    AxiClockConverterReference, CHANNELS, prepare_operations,
)
from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class AxiClockConverterTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axi_clock_converter")

    def test_directed_operations_cover_all_channels_and_backpressure(self):
        operations = prepare_operations([], self.case.parameters)
        self.assertEqual({CHANNELS[item["channel"]] for item in operations}, set(CHANNELS))
        self.assertTrue(any(item["hold"] for item in operations))

    def test_reference_zeros_fields_not_present_on_channel(self):
        operations = prepare_operations([], self.case.parameters)
        model = AxiClockConverterReference()
        rows = model.evaluate(operations)
        aw = next(row for row in rows if row["channel"] == 0)
        w = next(row for row in rows if row["channel"] == 1)
        self.assertEqual((aw["data"], aw["strb"], aw["resp"]), (0, 0, 0))
        self.assertEqual((w["id"], w["addr"], w["len"]), (0, 0, 0))
        self.assertEqual(set(model.event_counts) - {"backpressured"}, set(CHANNELS))

    def test_spec_enables_async_clocks_and_all_user_fields(self):
        spec = self.plugin.describe(self.case.parameters)
        self.assertEqual(spec.settings["ACLK_ASYNC"], 1)
        self.assertEqual(spec.settings["AWUSER_WIDTH"], self.case.parameters["user_width"])
        self.assertEqual(spec.model_parameters["C_AXI_SUPPORTS_USER_SIGNALS"], 1)

    def test_invalid_parameters_are_rejected(self):
        self.plugin.validate_case(self.case)
        for change in ({"data_width": 48}, {"address_width": 33}, {"id_width": 2},
                       {"user_width": 2}, {"synchronization_stages": 9},
                       {"output_period_ns": 7}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(
                    self.case, parameters={**self.case.parameters, **change}))

    def test_all_extended_parameters_validate_without_vivado(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/axi_clock_converter/extended.json")
        self.assertEqual(len(cases), 15750)
        for case in cases:
            self.plugin.validate_case(case)


if __name__ == "__main__":
    unittest.main()

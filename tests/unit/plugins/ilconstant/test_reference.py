from dataclasses import replace
from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.integer_literals import parse_unsigned_literal
from unit.plugins.cycle_helpers import plugin_case


class InlineConstantTests(unittest.TestCase):
    def test_literal_formats_and_width_are_independent_of_dut(self):
        plugin, _ = plugin_case("ilconstant")
        for text in ("85", "b1010101", "0125", "0x55", "0X55"):
            spec = plugin.describe({"width": 7, "value": text})
            self.assertEqual(spec.model_factory().step({}), {"dout": 85})
            self.assertEqual(spec.inputs, ())
            self.assertEqual(spec.settings["CONST_VAL"], text)

    def test_high4096_is_retained_and_fake_inputs_rejected(self):
        plugin, _ = plugin_case("ilconstant")
        model = plugin.describe({"width": 4096, "value": "0x8" + "0"*1023}).model_factory()
        self.assertEqual(model.step({}), {"dout": 1 << 4095})
        with self.assertRaises(ValueError):
            model.step({"fake": 0})

    def test_rejects_out_of_range_or_ambiguous_literals(self):
        plugin, _ = plugin_case("ilconstant")
        for value in (85, True, "-1", "08", "0b10", "b2", "1_0", " 1", "128", "0x80"):
            with self.subTest(value=value), self.assertRaises(PluginError):
                plugin.describe({"width": 7, "value": value})
        for width in (0,4097,True,1.0):
            with self.assertRaises(PluginError):
                plugin.describe({"width": width, "value": "1"})

    def test_constant_budget_and_input_timing_are_not_fabricated(self):
        plugin, case = plugin_case("ilconstant")
        plugin.validate_case(case)
        for profile in (replace(case.verification, case_budget=2),
                        replace(case.verification, timing_mode="random_gaps"),
                        replace(case.verification, coverage_targets=("port_boundaries",))):
            with self.assertRaises(PluginError):
                plugin.validate_case(replace(case, verification=profile))

    def test_matrix_counts_numeric_values_not_alternate_literal_spellings(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/ilconstant/extended.json")
        values = {(c.parameters["width"], parse_unsigned_literal(c.parameters["value"])) for c in cases}
        self.assertEqual(len(cases), 16861)
        self.assertEqual(len(values), len(cases))
        for width in range(1,4097):
            for value in (0,1,1 << (width-1),(1 << width)-1):
                self.assertIn((width,value), values)

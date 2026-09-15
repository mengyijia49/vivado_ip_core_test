from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class SliceTests(unittest.TestCase):
    def test_matrix_covers_all_input_widths_and_full_selected_range_spaces(self):
        cases = load_test_cases(Path(__file__).resolve().parents[4] / "configs/ip/xlslice/extended.json")
        parameters = {(c.parameters["input_width"], c.parameters["high_bit"], c.parameters["low_bit"])
                      for c in cases}
        self.assertEqual(len(parameters), 61580)
        self.assertEqual(len(parameters), len(cases))
        self.assertEqual({w for w, _, _ in parameters}, set(range(2, 4097)))
        for width in (*range(2, 33), 33, 65, 129, 256):
            self.assertEqual(sum(w == width for w, _, _ in parameters), width * (width + 1) // 2)

    def test_literal_bit_positions_and_single_bit_output(self):
        plugin, _ = plugin_case("xlslice")
        spec = plugin.describe({"input_width": 8, "high_bit": 5, "low_bit": 2})
        self.assertEqual(spec.model_factory().step({"Din": 0xDA}), {"Dout": 6})
        spec = plugin.describe({"input_width": 8, "high_bit": 7, "low_bit": 7})
        self.assertEqual(spec.model_factory().step({"Din": 0x80}), {"Dout": 1})
        self.assertFalse(spec.outputs[0].scalar)

    def test_all_small_inputs_match_explicit_bit_selection(self):
        plugin, _ = plugin_case("xlslice")
        for high in range(8):
            for low in range(high+1):
                model = plugin.describe({"input_width": 8, "high_bit": high, "low_bit": low}).model_factory()
                for value in range(256):
                    bits = f"{value:08b}"
                    self.assertEqual(model.step({"Din": value})["Dout"], int(bits[7-high:8-low], 2))

    def test_high_unused_inputs_do_not_leak_into_slice(self):
        plugin, _ = plugin_case("xlslice")
        spec = plugin.describe({"input_width": 4096, "high_bit": 255, "low_bit": 247})
        value = (1 << 4095) | (0x155 << 247) | ((1 << 247)-1)
        self.assertEqual(spec.model_factory().step({"Din": value}), {"Dout": 0x155})
        prefix = list(spec.prefix())
        for bit in range(247, 256):
            self.assertIn({"Din": 1 << bit}, prefix)
        self.assertIn({"Din": 1 << 246}, prefix)
        self.assertIn({"Din": 1 << 256}, prefix)

    def test_catalog_and_cross_field_limits_are_checked(self):
        plugin, case = plugin_case("xlslice")
        for change in ({"input_width": 1}, {"input_width": 4097}, {"high_bit": 256},
                       {"high_bit": 2}, {"low_bit": 1}, {"low_bit": -1}, {"high_bit": True}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                plugin.describe({**case.parameters, **change})

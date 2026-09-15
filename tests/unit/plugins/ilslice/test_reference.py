from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class InlineSliceTests(unittest.TestCase):
    def test_every_small_slice_matches_literal_bit_string_selection(self):
        plugin, _ = plugin_case("ilslice")
        for width in range(2, 9):
            for low in range(width):
                for high in range(low, width):
                    model = plugin.describe({"input_width": width, "high_bit": high, "low_bit": low}).model_factory()
                    for value in range(1 << width):
                        bits = format(value, f"0{width}b")
                        expected = int(bits[width-1-high:width-low], 2)
                        self.assertEqual(model.step({"Din": value}), {"Dout": expected})

    def test_bit4095_and_cross256_are_not_limited_to_static_xml_range(self):
        plugin, _ = plugin_case("ilslice")
        high = plugin.describe({"input_width": 4096, "high_bit": 4095, "low_bit": 4095})
        self.assertEqual(high.model_factory().step({"Din": 1 << 4095}), {"Dout": 1})
        self.assertEqual(high.model_factory().step({"Din": (1 << 4095)-1}), {"Dout": 0})
        cross = plugin.describe({"input_width": 4096, "high_bit": 263, "low_bit": 247})
        self.assertEqual(cross.model_factory().step({"Din": (1 << 263) | (1 << 247) | (1 << 246)}),
                         {"Dout": 65537})

    def test_directed_inputs_toggle_selected_and_adjacent_bits(self):
        plugin, _ = plugin_case("ilslice")
        spec = plugin.describe({"input_width": 4096, "high_bit": 263, "low_bit": 247})
        values = {f["Din"] for f in spec.prefix()}
        self.assertTrue({1 << bit for bit in range(246, 265)} <= values)
        self.assertIn(1 << 4095, values)

    def test_rejects_invalid_intervals_and_types(self):
        plugin, _ = plugin_case("ilslice")
        for width, high, low in ((1,0,0), (4097,0,0), (8,8,0), (8,2,3), (8,2,-1),
                                 (8,False,0), (8,2,1.0), (4096,4096,0)):
            with self.subTest(values=(width,high,low)), self.assertRaises(PluginError):
                plugin.describe({"input_width": width, "high_bit": high, "low_bit": low})

    def test_matrix_covers_all_widths_and_high_bits_with_unique_parameters(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/ilslice/extended.json")
        tuples = {(c.parameters["input_width"], c.parameters["high_bit"], c.parameters["low_bit"]) for c in cases}
        self.assertEqual(len(cases), 31119)
        self.assertEqual(len(tuples), len(cases))
        self.assertEqual({w for w,h,l in tuples}, set(range(2,4097)))
        for width in range(33,4097):
            self.assertIn((width,width-1,width-1), tuples)
            self.assertIn((width,width-1,0), tuples)

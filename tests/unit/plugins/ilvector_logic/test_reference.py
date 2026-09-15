from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class InlineVectorLogicTests(unittest.TestCase):
    def test_small_inputs_match_bitwise_truth_tables(self):
        plugin, _ = plugin_case("ilvector_logic")
        tables = {"and": (0,0,0,1), "or": (0,1,1,1), "xor": (0,1,1,0)}
        for width in range(1,5):
            for operation, table in tables.items():
                model = plugin.describe({"width":width,"operation":operation}).model_factory()
                for a in range(1 << width):
                    for b in range(1 << width):
                        expected = sum(table[2*((a >> bit)&1)+((b >> bit)&1)] << bit for bit in range(width))
                        self.assertEqual(model.step({"Op1":a,"Op2":b}),{"Res":expected})

    def test_not_omits_op2_and_preserves_65536_bits(self):
        plugin, _ = plugin_case("ilvector_logic")
        spec = plugin.describe({"width":65536,"operation":"not"})
        self.assertEqual([p.name for p in spec.inputs],["Op1"])
        self.assertFalse(spec.inputs[0].scalar)
        expected = (1 << 65535)-2
        self.assertEqual(spec.model_factory().step({"Op1":(1 << 65535)|1}),{"Res":expected})
        self.assertFalse(spec.outputs[0].scalar)

    def test_prefix_exposes_both_operands_under_zero_and_one_masks(self):
        plugin, _ = plugin_case("ilvector_logic")
        spec = plugin.describe({"width":33,"operation":"and"})
        frames = list(spec.prefix())
        limit = (1 << 33)-1
        first = {f["Op1"] for f in frames if f["Op2"] == limit}
        second = {f["Op2"] for f in frames if f["Op1"] == limit}
        self.assertEqual(first,second)
        signatures = {tuple((value >> bit)&1 for value in sorted(first)) for bit in range(33)}
        self.assertEqual(len(signatures),33)
        for value in first:
            self.assertIn({"Op1":value,"Op2":limit^value},frames)

    def test_parameters_are_copied_and_bad_values_rejected(self):
        plugin, _ = plugin_case("ilvector_logic")
        p = {"width":7,"operation":"xor"}
        spec = plugin.describe(p)
        p["operation"] = "and"
        self.assertEqual(spec.model_factory().step({"Op1":85,"Op2":42}),{"Res":127})
        for p in ({"width":0,"operation":"xor"},{"width":65537,"operation":"xor"},
                  {"width":True,"operation":"xor"},{"width":1.0,"operation":"xor"},
                  {"width":8,"operation":"nand"},{"width":8,"operation":"NOT"},
                  {"width":8,"operation":"and","unknown":1}):
            with self.subTest(parameters=p),self.assertRaises(PluginError):
                plugin.describe(p)

    def test_matrix_has_all_small_widths_and_distinct_wide_boundaries(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root/"configs/ip/ilvector_logic/extended.json")
        values = {(c.parameters["width"],c.parameters["operation"]) for c in cases}
        self.assertEqual(len(cases),16448)
        self.assertEqual(len(values),len(cases))
        for operation in ("and","or","xor","not"):
            self.assertTrue({(w,operation) for w in range(1,4097)} <= values)
            for w in (13000,13001,14285,14286,32767,32768,32769,65535,65536):
                self.assertIn((w,operation),values)

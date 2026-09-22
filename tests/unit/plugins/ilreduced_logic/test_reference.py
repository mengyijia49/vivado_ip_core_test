import json
from pathlib import Path
import tempfile
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.metadata import load_metadata
from unit.plugins.cycle_helpers import plugin_case
from unit.test_inline_metadata import write_design


class InlineReducedLogicTests(unittest.TestCase):
    def test_all_small_inputs_match_boolean_reduction(self):
        plugin, _ = plugin_case("ilreduced_logic")
        for width in range(1,9):
            for operation in ("and","or","xor"):
                model = plugin.describe({"width":width,"operation":operation}).model_factory()
                for value in range(1 << width):
                    bits = [bool(value & (1 << i)) for i in range(width)]
                    expected = all(bits) if operation == "and" else any(bits) if operation == "or" else sum(bits)%2
                    self.assertEqual(model.step({"Op1":value}),{"Res":int(expected)})

    def test_single_zero_or_one_at_every_position_is_driven(self):
        plugin, _ = plugin_case("ilreduced_logic")
        for width in (1,2,7,32,33,257):
            spec = plugin.describe({"width":width,"operation":"xor"})
            values = {f["Op1"] for f in spec.prefix()}
            for bit in range(width):
                self.assertIn(1 << bit,values)
                self.assertIn(((1 << width)-1)^(1 << bit),values)

    def test_wide_high_bits_and_odd_even_parity_remain_observable(self):
        plugin, _ = plugin_case("ilreduced_logic")
        for width in (65535,65536):
            model = plugin.describe({"width":width,"operation":"xor"}).model_factory()
            self.assertEqual(model.step({"Op1":1 << (width-1)}),{"Res":1})
            self.assertEqual(model.step({"Op1":(1 << (width-1))|1}),{"Res":0})
            self.assertEqual(model.step({"Op1":(1 << width)-1}),{"Res":width%2})

    def test_reduction_output_must_be_scalar_in_actual_bd(self):
        plugin, _ = plugin_case("ilreduced_logic")
        spec = plugin.describe({"width":1,"operation":"xor"})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = {"design":{
                "design_info":{"name":"dut_0","validated":"true","tool_version":"2026.1"},
                "design_tree":{"core":""},"components":{"core":{
                    "vlnv":"xilinx.com:inline_hdl:ilreduced_logic:1.0",
                    "parameters":{"C_SIZE":{"value":"1"},"C_OPERATION":{"value":"xor"}}}},
                "ports":{"Op1":{"direction":"I","left":"0","right":"0"},"Res":{"direction":"O"}},
                "nets":{name:{"ports":[name,"core/"+name]} for name in ("Op1","Res")}}}
            path = write_design(root,data)
            load_metadata(root,spec,"ilreduced_logic","1.0")
            data["design"]["ports"]["Res"].update({"left":"0","right":"0"})
            path.write_text(json.dumps(data))
            with self.assertRaises(PluginError):
                load_metadata(root,spec,"ilreduced_logic","1.0")

    def test_rejects_invalid_width_and_non_reduction_operation(self):
        plugin, _ = plugin_case("ilreduced_logic")
        for p in ({"width":0,"operation":"xor"},{"width":65537,"operation":"xor"},
                  {"width":True,"operation":"and"},{"width":8,"operation":"not"},
                  {"width":8,"operation":"xnor"},{"width":8,"operation":"xor","extra":False}):
            with self.subTest(parameters=p),self.assertRaises(PluginError):
                plugin.describe(p)

    def test_matrix_is_unique_and_keeps_all_widths_and_operations(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root/"configs/ip/ilreduced_logic/extended.json")
        values = {(c.parameters["width"],c.parameters["operation"]) for c in cases}
        self.assertEqual(len(cases),12336)
        self.assertEqual(len(values),len(cases))
        for operation in ("and","or","xor"):
            self.assertTrue({(w,operation) for w in range(1,4097)} <= values)
            self.assertIn((65535,operation),values)
            self.assertIn((65536,operation),values)

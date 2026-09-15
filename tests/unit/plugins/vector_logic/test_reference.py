import unittest

from unit.plugins.cycle_helpers import plugin_case


class VectorLogicReferenceTests(unittest.TestCase):
    def test_all_operations_and_width_mask(self):
        plugin, _ = plugin_case("vector_logic")
        for operation, expected in (("and", 0), ("or", 255), ("xor", 255), ("not", 170)):
            spec = plugin.describe({"width": 8, "operation": operation})
            frame = {"Op1": 85} if operation == "not" else {"Op1": 85, "Op2": 170}
            self.assertEqual(spec.model_factory().step(frame), {"Res": expected})
        self.assertEqual(plugin.describe({"width": 1, "operation": "not"}).model_factory().step({"Op1": 1}), {"Res": 0})

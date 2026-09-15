import unittest

from unit.plugins.cycle_helpers import plugin_case


class ReducedLogicReferenceTests(unittest.TestCase):
    def test_parity_all_bits_and_nonzero(self):
        plugin, _ = plugin_case("reduced_logic")
        for operation, values in (("and", [0, 0, 1]), ("or", [0, 1, 1]), ("xor", [0, 1, 0])):
            model = plugin.describe({"width": 8, "operation": operation}).model_factory()
            self.assertEqual([model.step({"Op1": value})["Res"] for value in (0, 1, 255)], values)

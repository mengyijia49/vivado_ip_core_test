import unittest

from unit.plugins.cycle_helpers import plugin_case


class MemoryReferenceTests(unittest.TestCase):
    def test_initial_data_write_collision_and_independent_read_address(self):
        plugin, case = plugin_case("distributed_memory")
        spec = plugin.describe(case.parameters)
        model = spec.model_factory()
        self.assertEqual(model.step(spec.frame()), {"spo": 341, "dpo": 341})
        self.assertEqual(model.step(spec.frame({"a": 47, "dpra": 47, "d": 7, "we": 1})),
                         {"spo": 7, "dpo": 7})
        self.assertEqual(model.step(spec.frame({"a": 0, "dpra": 47, "d": 8})),
                         {"spo": 341, "dpo": 7})

    def test_non_power_of_two_address_space_and_directed_readback(self):
        plugin, case = plugin_case("distributed_memory")
        spec = plugin.describe(case.parameters)
        self.assertEqual(spec.inputs[0].width, 6)
        self.assertEqual(spec.inputs[0].limit, 47)
        self.assertEqual(len(spec.prefix), 5 * 48)
        self.assertEqual({row["a"] for row in spec.prefix}, set(range(48)))

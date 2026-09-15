from itertools import product
import unittest

from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class TmrComparatorTests(unittest.TestCase):
    def setUp(self):
        self.plugin, case = plugin_case("tmr_comparator")
        self.p = dict(case.parameters)

    def test_one_bit_pairwise_and_voter_error_truth_table(self):
        spec = self.plugin.describe(self.p)
        model = spec.model_factory()
        pair_flags = (0, 6, 5, 3, 3, 5, 6, 0)
        for index, bits in enumerate(product((0, 1), repeat=3)):
            for voted in (0, 1):
                row = spec.frame(dict(zip(("Discrete1", "Discrete2", "Discrete3"), bits)))
                row["Discrete"] = voted
                expected = pair_flags[index] | int(voted != int(sum(bits) >= 2)) << 3
                self.assertEqual(model.step(row), {"Compare": expected})

    def test_disable_selects_first_replica_but_keeps_mismatch_flags(self):
        spec = self.plugin.describe({**self.p, "width": 8, "disable_port": True})
        model = spec.model_factory()
        row = spec.frame({"Discrete1": 1, "Discrete2": 0, "Discrete3": 0,
                          "Discrete": 1, "TMR_Disable": 1})
        self.assertEqual(model.step(row), {"Compare": 3})
        self.assertEqual(model.step({**row, "TMR_Disable": 0}), {"Compare": 11})

    def test_mask_only_controls_low_64_bits(self):
        spec = self.plugin.describe({**self.p, "width": 65, "include_mask": 0})
        model = spec.model_factory()
        self.assertEqual(model.step(spec.frame({"Discrete1": 1, "Discrete": 1})), {"Compare": 0})
        self.assertEqual(model.step(spec.frame({"Discrete1": 1 << 64})), {"Compare": 3})
        self.assertEqual(model.step(spec.frame({"Discrete": 1 << 64})), {"Compare": 8})

    def test_register_reset_and_lockstep_ports(self):
        spec = self.plugin.describe({**self.p, "triple": False, "voter_check": False,
                                     "input_register": True})
        self.assertEqual({port.name for port in spec.inputs}, {"Discrete1", "Discrete2", "Rst"})
        model = spec.model_factory()
        self.assertEqual(model.step(spec.frame({"Discrete1": 1})), {"Compare": 1})
        self.assertEqual(model.step(spec.frame({"Discrete1": 1, "Rst": 1})), {"Compare": 0})
        self.assertEqual(model.step(spec.frame({"Discrete1": 1})), {"Compare": 1})

    def test_prefix_includes_each_corrupted_voter_output_bit(self):
        spec = self.plugin.describe({**self.p, "width": 65})
        rows = list(spec.prefix())
        for bit in range(65):
            self.assertTrue(any(row["Discrete"] == 1 << bit and
                row["Discrete1"] == row["Discrete2"] == row["Discrete3"] == 0 for row in rows))

    def test_rejects_invalid_masks_and_inactive_controls(self):
        for updates in ({"include_mask": -1}, {"include_mask": 1 << 64},
                        {"include_mask": True}, {"triple": False},
                        {"voter_check": False, "disable_port": True}):
            with self.subTest(updates=updates), self.assertRaises(PluginError):
                self.plugin.describe({**self.p, **updates})

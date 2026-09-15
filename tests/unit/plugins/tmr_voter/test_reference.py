from itertools import product
import unittest

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import DefinedBits
from unit.plugins.cycle_helpers import plugin_case


class TmrVoterTests(unittest.TestCase):
    def setUp(self):
        self.plugin, case = plugin_case("tmr_voter")
        self.p = dict(case.parameters)

    def test_one_bit_truth_table_and_disable(self):
        for disabled in (0, 1):
            spec = self.plugin.describe({**self.p, "disable_port": True})
            model = spec.model_factory()
            for bits in product((0, 1), repeat=3):
                row = spec.frame(dict(zip(("Discrete1", "Discrete2", "Discrete3"), bits)))
                row["TMR_Disable"] = disabled
                expected = bits[0] if disabled else int(sum(bits) >= 2)
                self.assertEqual(model.step(row), {"Discrete": expected})

    def test_lane_majority_is_not_whole_word_selection(self):
        spec = self.plugin.describe({**self.p, "width": 3, "comparator": True, "voter_check": True})
        result = spec.model_factory().step(spec.frame({"Discrete1": 3, "Discrete2": 5, "Discrete3": 6}))
        self.assertEqual(result, {"Discrete": 7, "Compare": 7})

    def test_lockstep_registered_compare_has_no_reset_and_only_bit_zero_is_defined(self):
        spec = self.plugin.describe({**self.p, "width": 8, "triple": False,
                                     "comparator": True, "input_register": True})
        self.assertEqual(spec.clock, "Clk")
        self.assertEqual(spec.outputs[1].width, 4)
        self.assertFalse(spec.outputs[1].scalar)
        self.assertNotIn("Rst", {port.name for port in spec.inputs})
        self.assertTrue(spec.masked_outputs)
        model = spec.model_factory()
        frame = spec.frame({"Discrete1": 0xA5, "Discrete2": 0x5A})
        self.assertEqual(model.step(frame), {"Discrete": 0xA5,
            "Compare": DefinedBits(1, 1, "lockstep_unused_compare_bits")})
        self.assertEqual(model.step({**frame, "Discrete2": 0xA5}), {"Discrete": 0xA5,
            "Compare": DefinedBits(0, 1, "lockstep_unused_compare_bits")})

    def test_prefix_exercises_every_lane_and_disable(self):
        spec = self.plugin.describe({**self.p, "width": 65, "disable_port": True})
        rows = list(spec.prefix())
        for bit in range(65):
            for disabled in (0, 1):
                self.assertTrue(any(row["Discrete1"] == 1 << bit and
                    row["Discrete2"] == row["Discrete3"] == 0 and
                    row["TMR_Disable"] == disabled for row in rows))

    def test_prefix_contains_disjoint_faults_and_their_complements(self):
        spec = self.plugin.describe({**self.p, "width": 65})
        rows = list(spec.prefix())
        model = spec.model_factory()
        full = (1 << 65) - 1
        for bit in range(65):
            for invert in (0, full):
                values = [1 << ((bit + i) % 65) ^ invert for i in range(3)]
                row = spec.frame(dict(zip(("Discrete1", "Discrete2", "Discrete3"), values)))
                self.assertIn(row, rows)
                self.assertNotIn(invert, values)
                self.assertEqual(model.step(row)["Discrete"], invert)

    def test_rejects_inactive_parameters(self):
        for updates in ({"width": True}, {"width": 0}, {"width": 1025},
                        {"input_register": True}, {"voter_check": True},
                        {"include_mask": 0}, {"triple": False, "disable_port": True}):
            with self.subTest(updates=updates), self.assertRaises(PluginError):
                self.plugin.describe({**self.p, **updates})

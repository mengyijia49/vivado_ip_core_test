from dataclasses import replace
import unittest

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import DefinedBits
from unit.plugins.cycle_helpers import plugin_case


class BlockMemoryTests(unittest.TestCase):
    def model(self, **changes):
        plugin, case = plugin_case("block_memory")
        spec = plugin.describe({**case.parameters, **changes})
        return spec, spec.model_factory()

    def test_three_write_modes_and_readback(self):
        for mode, during_write in (("READ_FIRST", 165), ("WRITE_FIRST", 4660), ("NO_CHANGE", 165)):
            with self.subTest(mode=mode):
                spec, model = self.model(write_mode_a=mode)
                model.step(spec.frame({"addra": 3}))
                self.assertEqual(model.step(spec.frame({"addra": 3, "wea": 1, "dina": 4660}))["douta"], during_write)
                self.assertEqual(model.step(spec.frame({"addra": 3}))["douta"], 4660)

    def test_byte_write_changes_only_selected_lane_and_masks_only_unspecified_output(self):
        spec, model = self.model(byte_size=8, write_mode_a="WRITE_FIRST", initial_value=0xA5A5)
        output = model.step(spec.frame({"wea": 1, "dina": 0x1234}))["douta"]
        self.assertIsInstance(output, DefinedBits)
        self.assertEqual(output.mask, 0)
        self.assertEqual(model.step(spec.frame())["douta"], 0xA534)

    def test_regce_is_independent_of_ena_and_reset_does_not_erase_memory(self):
        spec, model = self.model(output_register=True, register_enable=True, reset_memory_latch=True)
        model.step(spec.frame({"wea": 1, "dina": 11}))
        model.step(spec.frame({"regcea": 0}))
        self.assertEqual(model.step(spec.frame({"ena": 0}))["douta"], 11)
        self.assertEqual(model.step(spec.frame({"ena": 0, "rsta": 1}))["douta"], 0)
        self.assertEqual(model.step(spec.frame({"ena": 0}))["douta"], 11)
        self.assertEqual(model.memory[0][0], 11)

    def test_dual_port_old_data_and_partial_collision_recovery(self):
        spec, model = self.model(memory_type="True_Dual_Port_RAM", byte_size=8, initial_value=0)
        self.assertEqual(model.step(spec.frame({"wea": 1, "dina": 0xAA, "web": 2, "dinb": 0xBB00})),
                         {"douta": 0, "doutb": 0})
        self.assertEqual(model.step(spec.frame()), {"douta": 0xBBAA, "doutb": 0xBBAA})
        model.step(spec.frame({"wea": 1, "dina": 0x11, "web": 1, "dinb": 0x22}))
        result = model.step(spec.frame())["douta"]
        self.assertEqual(result.mask, 0xFF00)
        self.assertEqual(result.value & result.mask, 0xBB00)
        model.step(spec.frame({"wea": 1, "dina": 0xCC}))
        self.assertEqual(model.step(spec.frame()), {"douta": 0xBBCC, "doutb": 0xBBCC})

    def test_cross_port_write_first_masks_only_written_bytes(self):
        spec, model = self.model(memory_type="True_Dual_Port_RAM", byte_size=8,
                                 write_mode_a="WRITE_FIRST", initial_value=0xABCD)
        result = model.step(spec.frame({"wea": 1, "dina": 0x22}))["doutb"]
        self.assertEqual(result.mask, 0xFF00)
        self.assertEqual(result.value & result.mask, 0xAB00)
        self.assertEqual(model.step(spec.frame())["doutb"], 0xAB22)

    def test_alias_clock_prefix_and_final_address_sweep(self):
        spec, _ = self.model(memory_type="Simple_Dual_Port_RAM")
        self.assertEqual(spec.clock_aliases, ("clkb",))
        self.assertTrue(callable(spec.prefix))
        self.assertEqual([f["addrb"] for f in spec.suffix()], list(range(32)))
        self.assertTrue(any(f.get("wea", 0) for f in spec.prefix()))

    def test_dual_port_prefix_covers_disjoint_collision_and_recovery(self):
        spec, model = self.model(memory_type="True_Dual_Port_RAM", byte_size=8)
        for frame in spec.prefix():
            model.step(spec.frame(frame))
        for event in ("overlapping_dual_write", "disjoint_dual_write", "cross_port_same_address_access"):
            self.assertGreater(model.event_counts[event], 0, event)
        self.assertTrue(all(mask == model.limit for _, mask in model.memory))

    def test_invalid_combinations_fail_before_vivado(self):
        plugin, case = plugin_case("block_memory")
        for change in ({"byte_size": 8, "write_mode_a": "NO_CHANGE"}, {"byte_size": 9},
            {"register_enable": True}, {"reset_memory_latch": True}, {"write_mode_b": "WRITE_FIRST"},
            {"width": 1}, {"memory_type": "Simple_Dual_Port_RAM", "write_mode_a": "WRITE_FIRST"}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                plugin.validate_case(replace(case, parameters={**case.parameters, **change}))

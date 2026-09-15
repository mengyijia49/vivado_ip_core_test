from dataclasses import replace
from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.bit_patterns import bit_identity_frames
from vivado_ip_test.plugins.common.cycle import Port
from unit.plugins.cycle_helpers import plugin_case


class ConcatTests(unittest.TestCase):
    def test_matrix_has_unique_arrays_and_all_port_counts(self):
        cases = load_test_cases(Path(__file__).resolve().parents[4] / "configs/ip/xlconcat/extended.json")
        arrays = {tuple(case.parameters["input_widths"]) for case in cases}
        self.assertEqual(len(cases), 15014)
        self.assertEqual(len(arrays), len(cases))
        self.assertEqual({len(widths) for widths in arrays}, set(range(1, 129)))
        self.assertIn((4096,) * 128, arrays)
        for lane in (0, 63, 127):
            widths = [1] * 128
            widths[lane] = 4096
            self.assertIn(tuple(widths), arrays)

    def test_in0_is_low_and_unequal_ports_keep_all_bits(self):
        plugin, _ = plugin_case("xlconcat")
        spec = plugin.describe({"input_widths": [1, 3, 4]})
        self.assertEqual(spec.model_factory().step({"In0": 1, "In1": 2, "In2": 10}), {"dout": 0xA5})
        self.assertEqual([p.width for p in spec.inputs], [1, 3, 4])
        self.assertEqual(spec.outputs[0].width, 8)

    def test_spec_copies_width_list_and_keeps_one_bit_vectors(self):
        plugin, _ = plugin_case("xlconcat")
        p = {"input_widths": [1, 2]}
        spec = plugin.describe(p)
        p["input_widths"][0] = 4096
        self.assertEqual(spec.model_factory().step({"In0": 1, "In1": 2}), {"dout": 5})
        self.assertFalse(spec.inputs[0].scalar)

    def test_each_physical_bit_has_unique_nonconstant_temporal_signature(self):
        ports = (Port("a", 1), Port("b", 7), Port("c", 33))
        frames = list(bit_identity_frames(ports))
        signatures = [tuple((f[p.name] >> bit) & 1 for f in frames) for p in ports for bit in range(p.width)]
        self.assertEqual(len(set(signatures)), 41)
        self.assertTrue(all(set(s) == {0, 1} for s in signatures))
        self.assertEqual(len(frames), 14)

    def test_wide_last_port_is_not_truncated_to_machine_integer(self):
        plugin, _ = plugin_case("xlconcat")
        spec = plugin.describe({"input_widths": [4096] * 128})
        frame = spec.frame({"In127": 1 << 4095, "In0": 1})
        self.assertEqual(spec.model_factory().step(frame)["dout"], (1 << 524287) | 1)
        self.assertEqual(spec.outputs[0].width, 524288)

    def test_invalid_width_arrays_are_rejected(self):
        plugin, _ = plugin_case("xlconcat")
        for widths in ([], [1] * 129, [0], [4097], [True], [1.0], "1,2", (1, 2)):
            with self.subTest(widths=str(widths)[:40]), self.assertRaises(PluginError):
                plugin.describe({"input_widths": widths})
        with self.assertRaises(PluginError):
            plugin.describe({"input_widths": [1], "ports": 1})

    def test_small_space_is_exhaustive_and_request_uses_block_design_xci(self):
        plugin, case = plugin_case("xlconcat")
        plugin.validate_case(case)
        self.assertIn("/bd/dut_0/", plugin.build_request(case).artifact_glob)
        with self.assertRaises(PluginError):
            plugin.validate_case(replace(case, verification=replace(case.verification, case_budget=1)))

from dataclasses import replace
from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.domain import Status
from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class InlineConcatTests(unittest.TestCase):
    def test_unequal_ports_have_literal_expected_order(self):
        plugin, _ = plugin_case("ilconcat")
        spec = plugin.describe({"input_widths": [1, 3, 4]})
        self.assertEqual(spec.model_factory().step({"In0": 1, "In1": 2, "In2": 10}), {"dout": 0xA5})
        self.assertTrue(all(not p.scalar for p in spec.inputs))

    def test_widest_last_port_and_original_list_are_preserved(self):
        plugin, _ = plugin_case("ilconcat")
        widths = [4096]*128
        spec = plugin.describe({"input_widths": widths})
        widths[0] = 1
        self.assertEqual(spec.outputs[0].width, 524288)
        self.assertEqual(spec.model_factory().step(spec.frame({"In0": 1, "In127": 1 << 4095})),
                         {"dout": (1 << 524287) | 1})

    def test_rejects_bad_arrays_and_bad_budget(self):
        plugin, case = plugin_case("ilconcat")
        for widths in ([], [1]*129, [0], [4097], [True], [1.0], "1", (1,)):
            with self.subTest(widths=str(widths)[:40]), self.assertRaises(PluginError):
                plugin.describe({"input_widths": widths})
        with self.assertRaises(PluginError):
            plugin.validate_case(replace(case, verification=replace(case.verification, case_budget=1)))

    def test_build_uses_own_inline_tcl_and_bd_not_legacy_xci(self):
        plugin, case = plugin_case("ilconcat")
        request = plugin.build_request(case)
        self.assertEqual(request.source_path.parts[-3:], ("ip", "ilconcat", "create_ip.tcl"))
        self.assertTrue(request.artifact_glob.endswith("/dut_0.bd"))
        self.assertEqual(request.missing_artifact_status, Status.BLOCK_DESIGN_NOT_FOUND)

    def test_matrix_covers_port_counts_and_outlier_positions_without_duplicates(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/ilconcat/extended.json")
        arrays = {tuple(c.parameters["input_widths"]) for c in cases}
        self.assertEqual(len(cases), 10872)
        self.assertEqual(len(arrays), len(cases))
        self.assertEqual({len(w) for w in arrays}, set(range(1, 129)))
        self.assertIn((4096,)*128, arrays)
        for lane in range(128):
            widths = [1]*128
            widths[lane] = 4096
            self.assertIn(tuple(widths), arrays)

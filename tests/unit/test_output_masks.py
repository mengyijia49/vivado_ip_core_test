from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.infrastructure.output import first_output_difference, output_files_match
from vivado_ip_test.plugins.common.cycle import DefinedBits
from vivado_ip_test.plugins.common.testbench import normalize_expected, render_testbench
from vivado_ip_test.services.failure_analysis import analyze_outputs
from unit.plugins.cycle_helpers import plugin_case


class OutputMaskTests(unittest.TestCase):
    def test_mask_ignores_only_undefined_bits_and_keeps_first_real_difference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectors").mkdir()
            (root / "outputs").mkdir()
            expected, actual, mask = root / "vectors/expected_output.txt", root / "outputs/actual_output.txt", root / "vectors/expected_mask.txt"
            expected.write_text("01\n10\n")
            actual.write_text("X1\n10\n")
            mask.write_text("01\n11\n")
            self.assertTrue(output_files_match(expected, actual, mask_path=mask))
            actual.write_text("X1\n1U\n")
            difference = analyze_outputs(root)
            self.assertEqual(difference["output_index"], 1)
            self.assertEqual(difference["expected_mask"], "11")
            self.assertEqual(difference["kind"], "value_mismatch")
            self.assertTrue(difference["contains_unknown_bits"])

    def test_missing_malformed_extra_or_vacuous_masks_never_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected, actual, mask = (root / name for name in ("expected", "actual", "mask"))
            expected.write_text("01\n")
            actual.write_text("01\n")
            self.assertEqual(first_output_difference(expected, actual, mask_path=mask)["kind"], "missing_mask_artifact")
            for text in ("", "0\n", "0X\n", "11\n11\n", "00\n"):
                with self.subTest(mask=text):
                    mask.write_text(text)
                    self.assertFalse(output_files_match(expected, actual, mask_path=mask))

    def test_expected_and_actual_must_have_correct_binary_shape(self):
        with tempfile.TemporaryDirectory() as directory:
            e, a = Path(directory) / "e", Path(directory) / "a"
            for expected, actual in (("X", "X"), ("01", "0"), ("", ""), ("01", "ab")):
                e.write_text(expected + "\n")
                a.write_text(actual + "\n")
                self.assertFalse(output_files_match(e, a))

    def test_failure_analysis_survives_malformed_mapping_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectors").mkdir()
            (root / "outputs").mkdir()
            (root / "vectors/expected_output.txt").write_text("0\n")
            (root / "outputs/actual_output.txt").write_text("1\n")
            (root / "manifest.json").write_text("[]")
            (root / "vectors/schedule.json").write_text("[]")
            difference = analyze_outputs(root)
            self.assertEqual(difference["kind"], "value_mismatch")
            self.assertFalse(difference["input_mapping_available"])

    def test_defined_bits_require_reason_and_explicit_opt_in(self):
        plugin, case = plugin_case("vector_logic")
        spec = plugin.describe(case.parameters)
        with self.assertRaises(ValueError):
            normalize_expected(spec, {"Res": DefinedBits(0, 0, "undefined")})
        spec = replace(spec, masked_outputs=True)
        for result in (DefinedBits(0, 0, ""), DefinedBits(0, 256, "outside"), DefinedBits(True, 1, "boolean")):
            with self.subTest(result=result), self.assertRaises(ValueError):
                normalize_expected(spec, {"Res": result})

    def test_generator_rejects_a_port_that_is_never_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("vector_logic", Path(directory))
            spec = replace(plugin.describe(case.parameters), masked_outputs=True,
                           model_factory=lambda: type("Undefined", (), {"step": lambda self, f: {"Res": DefinedBits(0, 0, "undefined")}})())
            fixture = Path(directory) / "fixture.xci"
            fixture.write_text("{}")
            with patch("vivado_ip_test.plugins.common.testbench.load_metadata", return_value=(fixture, {})), self.assertRaises(ValueError):
                plugin._backend.generate(case, spec, plugin.ip_name, plugin.version)

    def test_generated_mask_file_is_hashed_and_hdl_preserves_raw_output(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("fifo_generator", Path(directory))
            fixture = Path(directory) / "fixture.xci"
            fixture.write_text("{}")
            with patch("vivado_ip_test.plugins.common.testbench.load_metadata", return_value=(fixture, {})):
                artifacts = plugin.generate_testbench(case)
            manifest = json.loads(artifacts.manifest_path.read_text())
            self.assertIn("expected_mask", manifest["artifact_sha256"])
            text = artifacts.testbench_path.read_text()
            self.assertIn("actual and expected_mask", text)
            self.assertLess(text.index("writeline(actual_file"), text.index("assert not is_x(actual"))
            self.assertTrue(all(count > 0 for count in artifacts.metrics["defined_output_bits_by_port"].values()))
            self.assertGreater(artifacts.metrics["masked_output_bits"], 0)

    def test_fully_undefined_cycles_do_not_inflate_checked_count(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("block_memory", Path(directory))
            case = replace(case, parameters={**case.parameters, "byte_size": 8,
                                             "write_mode_a": "WRITE_FIRST"})
            fixture = Path(directory) / "fixture.xci"
            fixture.write_text("{}")
            with patch("vivado_ip_test.plugins.common.testbench.load_metadata", return_value=(fixture, {})):
                artifacts = plugin.generate_testbench(case)
            masks = (artifacts.expected_path.parent / "expected_mask.txt").read_text().splitlines()
            full = sum("1" not in mask for mask in masks)
            self.assertGreater(full, 0)
            self.assertEqual(artifacts.metrics["fully_masked_cycles"], full)
            self.assertEqual(artifacts.metrics["checked_transaction_count"], len(masks) - full)

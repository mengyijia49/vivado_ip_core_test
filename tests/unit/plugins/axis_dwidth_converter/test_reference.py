from dataclasses import replace
import json
from pathlib import Path
import tempfile
import tracemalloc
import unittest
from unittest.mock import patch

from vivado_ip_test.domain import Stage, Status
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.stream.bytes import expected_bytes, raw_output_tokens
from vivado_ip_test.plugins.common.stream.byte_testbench import raw_audit
from vivado_ip_test.plugins.common.testbench import packed
from vivado_ip_test.plugins.axis_dwidth_converter.vectors import prepare_frames
from unit.plugins.cycle_helpers import plugin_case


class WidthConverterTests(unittest.TestCase):
    def setUp(self):
        self.plugin, case = plugin_case("axis_dwidth_converter")
        self.p = {**case.parameters, "input_bytes": 4, "output_bytes": 2,
                  "has_keep": True, "has_strb": True, "id_width": 3, "dest_width": 2,
                  "user_bits_per_byte": 4}

    def test_data_position_null_user_and_packet_boundary(self):
        spec = self.plugin.describe(self.p)
        result = expected_bytes([{"tdata": 0x44332211, "tkeep": 0b1011, "tstrb": 0b1001,
            "tlast": 1, "tid": 5, "tdest": 3, "tuser": 0xDCBA}], spec.payload)
        rows, masks, required = zip(*result)
        self.assertEqual([r["data"] for r in rows], [0x11, 0x22, 0x44, 0])
        self.assertEqual([r["data_byte"] for r in rows], [1, 0, 1, 0])
        self.assertEqual([r["end_packet"] for r in rows], [0, 0, 0, 1])
        self.assertEqual([r["tuser"] for r in rows], [10, 11, 13, 0])
        self.assertEqual([r["data"] for r in masks], [255, 0, 255, 0])
        self.assertEqual([r["tid"] for r in rows], [5] * 4)
        self.assertEqual(required, (1, 1, 1, 1))
        self.assertEqual(result.count, 4)

    def test_null_transfer_drops_but_empty_packet_survives(self):
        spec = self.plugin.describe(self.p)
        empty = {port.name: 0 for port in spec.payload}
        result = expected_bytes([empty, {**empty, "tlast": 1}, {**empty, "tlast": 1}], spec.payload)
        self.assertEqual(result.count, 2)
        self.assertTrue(all(row["end_packet"] for row, _, _ in result))
        self.assertEqual(tuple(required for _, _, required in result), (2, 3))

    def test_raw_beat_audit_allows_null_padding_but_catches_qualified_changes(self):
        spec = self.plugin.describe(self.p)
        source = {"tdata": 0x44332211, "tkeep": 11, "tstrb": 9,
                  "tlast": 1, "tid": 5, "tdest": 3, "tuser": 0xDCBA}
        expected = expected_bytes([source], spec.payload)
        rows, masks, _ = zip(*expected)
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            (run / "vectors").mkdir()
            (run / "outputs").mkdir()
            for name, values in (("expected_output", rows), ("expected_mask", masks)):
                (run / f"vectors/{name}.txt").write_text("".join(packed(row, expected.ports) + "\n" for row in values))
            raw = run / "outputs/accepted_output.txt"
            beats = ["XXXXXXXX00010001" + "01" + "11" + "0" + "101" + "11" + "10111010",
                     "XXXXXXXX01000100" + "01" + "01" + "1" + "101" + "11" + "XXXX1101"]
            raw.write_text("\n".join(beats) + "\n")
            self.assertEqual(len(list(raw_output_tokens(raw, spec.sink_payload))), 4)
            self.assertTrue(raw_audit(run, spec))
            raw.write_text("\n".join([beats[0].replace("00010001", "00010000"), beats[1]]) + "\n")
            self.assertFalse(raw_audit(run, spec))
            raw.write_text("\n".join(beats[:-1]) + "\n")
            self.assertFalse(raw_audit(run, spec))

    def test_prepare_is_deterministic_preserves_numeric_rows_and_has_qualifier_edges(self):
        spec = self.plugin.describe(self.p)
        generated = [{port.name: port.limit for port in spec.generated_ports} for _ in range(8)]
        rows = prepare_frames(generated, self.p, spec)
        self.assertEqual(rows, prepare_frames(generated, self.p, spec))
        self.assertEqual([{p.name: row[p.name] for p in spec.generated_ports} for row in rows[-8:]], generated)
        self.assertTrue(any(row["tkeep"] == 0 and row["tlast"] for row in rows))
        for lane in range(4):
            self.assertTrue(any(row["tkeep"] == 1 << lane for row in rows))
        self.assertTrue(any(row["tkeep"] and not row["tstrb"] for row in rows))
        self.assertTrue(all(row["tstrb"] & ~row["tkeep"] == 0 for row in rows))

    def test_reserved_qualifier_is_not_treated_as_null(self):
        spec = self.plugin.describe(self.p)
        frame = {p.name: 0 for p in spec.payload}
        with self.assertRaisesRegex(ValueError, "Reserved"):
            expected_bytes([{**frame, "tstrb": 1}], spec.payload)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw.txt"
            bad = {p.name: 0 for p in spec.sink_payload}
            path.write_text(packed({**bad, "tstrb": 1}, spec.sink_payload) + "\n")
            with self.assertRaisesRegex(ValueError, "Reserved"):
                list(raw_output_tokens(path, spec.sink_payload))
            known = packed(bad, spec.sink_payload)
            path.write_text(known[:16] + "X0" + known[18:] + "\n")
            with self.assertRaisesRegex(ValueError, "Unknown"):
                list(raw_output_tokens(path, spec.sink_payload))

    def test_absent_strb_defaults_to_keep(self):
        spec = self.plugin.describe({**self.p, "has_strb": False})
        frame = {p.name: 0 for p in spec.payload}
        self.assertEqual(list(expected_bytes([frame], spec.payload)), [])

    def test_wide_reference_is_streamed_and_repeatable(self):
        spec = self.plugin.describe({**self.p, "input_bytes": 64, "output_bytes": 1})
        frame = {p.name: p.limit for p in spec.payload}
        tracemalloc.start()
        try:
            result = expected_bytes([frame] * 512, spec.payload)
            self.assertEqual(result.count, 512 * 65)
            first = next(iter(result))
            self.assertEqual(sum(1 for _ in result), result.count)
            self.assertEqual(next(iter(result)), first)
            self.assertLess(tracemalloc.get_traced_memory()[1], 2_000_000)
        finally:
            tracemalloc.stop()

    def test_continuous_mode_completes_last_metadata_group(self):
        p = {**self.p, "input_bytes": 3, "output_bytes": 5, "has_last": False, "has_keep": False}
        spec = self.plugin.describe(p)
        generated = [{port.name: 1 for port in spec.generated_ports} for _ in range(3)]
        rows = prepare_frames(generated, p, spec)
        tail = 0
        for row in reversed(rows):
            if (row["tid"], row["tdest"]) != (1, 1):
                break
            tail += 1
        self.assertEqual(tail % 5, 0)
        self.assertNotIn("tlast", rows[-1])

    def test_generated_output_keep_and_user_widths_are_checked(self):
        p = {**self.p, "input_bytes": 1, "output_bytes": 4, "has_keep": False}
        spec = self.plugin.describe(p)
        self.assertNotIn("s_axis_tkeep", {p.name for p in spec.inputs})
        self.assertIn("m_axis_tkeep", {p.name for p in spec.outputs})
        self.assertEqual({p.name: p.width for p in spec.outputs}["m_axis_tuser"], 16)
        self.assertEqual(spec.settings["HAS_MI_TKEEP"], 1)

    def test_bad_parameters_rejected(self):
        for change in ({"input_bytes": 0}, {"output_bytes": 513}, {"input_bytes": True},
                       {"id_width": 33}, {"output_bytes": 512, "user_bits_per_byte": 9}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                self.plugin.describe({**self.p, **change})

    def test_backend_writes_masks_causal_map_and_requires_raw_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("axis_dwidth_converter", Path(directory))
            xci = Path(directory) / "fake.xci"
            xci.write_text("{}")
            with patch("vivado_ip_test.plugins.common.stream.byte_testbench.load_metadata", return_value=(xci, {})):
                artifacts = plugin.generate_testbench(case)
            manifest = json.loads(artifacts.manifest_path.read_text())
            self.assertIn("required_inputs", manifest["artifact_sha256"])
            self.assertIn("expected_mask", manifest["artifact_sha256"])
            self.assertIn("raw_output", manifest["artifacts"])
            self.assertEqual(artifacts.metrics["comparison_kind"], "axis_byte_and_packet_tokens")
            self.assertIn("sent >= required_count", artifacts.testbench_path.read_text())
            artifacts.actual_path.write_bytes(artifacts.expected_path.read_bytes())
            Path(manifest["artifacts"]["accepted_input"]).write_bytes(artifacts.input_path.read_bytes())
            self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.VERIFICATION_FAILED)

    def test_backend_rejects_wrong_reference_count(self):
        def wrong_count(frames, payload):
            value = expected_bytes(frames, payload)
            return replace(value, count=value.count + 1)

        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("axis_dwidth_converter", Path(directory))
            xci = Path(directory) / "fake.xci"
            xci.write_text("{}")
            with patch("vivado_ip_test.plugins.common.stream.byte_testbench.load_metadata", return_value=(xci, {})), \
                    patch("vivado_ip_test.plugins.axis_dwidth_converter.plugin.expected_transactions", side_effect=wrong_count):
                with self.assertRaisesRegex(ValueError, "count differs"):
                    plugin.generate_testbench(case)

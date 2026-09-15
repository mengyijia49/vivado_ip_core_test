import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.axis_subset_converter.remap import build_remaps, evaluate, parse_remap
from vivado_ip_test.plugins.axis_subset_converter.reference import expected_transactions
from vivado_ip_test.plugins.axis_subset_converter.vectors import prepare_frames
from unit.plugins.cycle_helpers import plugin_case


class SubsetConverterTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axis_subset_converter")
        self.p = {**self.case.parameters, "input_bytes": 3, "output_bytes": 5,
                  "input_user_width": 17, "output_user_width": 24}

    def expected(self, changes, frames):
        p = {**self.p, **changes}
        spec = self.plugin.describe(p)
        return expected_transactions(frames, p, spec.payload, spec.sink_payload)

    def test_presets_against_known_values(self):
        frame = dict(tdata=0x123456, tuser=0x1ABCD, tstrb=7, tkeep=7, tlast=1)
        for mapping, wanted in {"resize": 0x123456, "reverse_bytes": 0x563412,
                "reverse_bits": 0x6A2C48, "rotate_bytes": 0x345612,
                "repeat_low_byte": 0x5656565656, "user_to_data": 0x1ABCD,
                "data_user_swap": 0x1ABCD}.items():
            with self.subTest(mapping=mapping):
                row = self.expected({"mapping": mapping}, [frame])[0]
                self.assertEqual(row["tdata"], wanted)
                self.assertEqual(row["tuser"], 0x123456 if mapping == "data_user_swap" else 0x1ABCD)
                self.assertEqual(row["tkeep"], 31)
                self.assertEqual(row["tstrb"], 31)

    def test_custom_concatenation_constants_and_cross_field_slices(self):
        parts = parse_remap("3'b101,TDATA[3:0],tid[1]", {"tdata": 16, "tid": 2}, 8)
        self.assertEqual(evaluate(parts, {"tdata": 0x1B, "tid": 2}), 0xB7)
        frame = dict(tdata=0x123456, tuser=0x1ABCD, tstrb=7, tkeep=7, tlast=1)
        original = dict(frame)
        row = self.expected({"remap": {"tdata": "8'b10100101,tuser[15:0],tdata[15:0]",
                                      "tlast": "tdata[0]"}}, [frame])[0]
        self.assertEqual(row["tdata"], 0xA5ABCD3456)
        self.assertEqual(row["tlast"], 0)
        self.assertEqual(frame, original)

    def test_parser_rejects_bad_widths_slices_and_executable_text(self):
        for text in ("", "8'hA5", "8'b1", "0'b0", "8'bXXXX0000", "tdata[8:1]",
                     "tdata[0:7]", "tuser[7:0]", "tdata[7:0],", "{tdata[7:0]}",
                     "tdata[7:0];exec", "tdata[7:0]+1", "tdata[-1]"):
            with self.subTest(text=text), self.assertRaises(PluginError):
                parse_remap(text, {"tdata": 8}, 8)

    def test_preset_tcl_mapping_agrees_with_independent_numeric_model(self):
        rng = random.Random(503)
        for n, m in ((1, 3), (3, 1), (5, 7), (7, 5)):
            for mode in ("resize", "reverse_bytes", "reverse_bits", "rotate_bytes", "repeat_low_byte"):
                p = {**self.p, "input_bytes": n, "output_bytes": m, "mapping": mode}
                spec = self.plugin.describe(p)
                widths = {port.name: port.width for port in spec.payload}
                parts = parse_remap(build_remaps(p, spec.payload, spec.sink_payload)["tdata"], widths, 8 * m)
                frames = [{port.name: (port.limit if port.name in {"tkeep", "tstrb"}
                            else rng.randrange(port.limit + 1)) for port in spec.payload} for _ in range(20)]
                expected = expected_transactions(frames, p, spec.payload, spec.sink_payload)
                self.assertEqual([evaluate(parts, frame) for frame in frames], [row["tdata"] for row in expected])

    def test_generated_last_counts_accepted_beats_and_wraps(self):
        for period in (0, 1, 2, 3, 7, 127, 128, 255, 256):
            p = {**self.p, "input_has_last": False, "last_period": period}
            spec = self.plugin.describe(p)
            frame = {port.name: port.limit for port in spec.payload}
            rows = expected_transactions([frame] * (2 * period + 3), p, spec.payload, spec.sink_payload)
            self.assertEqual([i + 1 for i, row in enumerate(rows) if row["tlast"]],
                             list(range(period, len(rows) + 1, period)) if period else [])
            if period:
                self.assertEqual(spec.settings["TLAST_REMAP"], "tlast[0]")

    def test_walking_bits_and_counter_prefix_preserve_supplied_tail(self):
        p = {**self.p, "input_has_last": False, "last_period": 256}
        spec = self.plugin.describe(p)
        tail = [{port.name: port.limit for port in spec.payload}]
        frames = prepare_frames(tail, spec, 256)
        self.assertGreaterEqual(len(frames), 515)
        self.assertEqual(frames[-1:], tail)
        for port in spec.generated_ports:
            values = {frame[port.name] for frame in frames}
            for bit in range(port.width):
                self.assertIn(1 << bit, values)
                self.assertIn(port.limit ^ (1 << bit), values)

    def test_sideband_only_ports_and_internal_padding(self):
        p = {**self.p, "input_bytes": 0, "output_bytes": 0, "mapping": "resize",
             "input_has_keep": False, "output_has_keep": False,
             "input_has_strb": False, "output_has_strb": False}
        spec = self.plugin.describe(p)
        self.assertNotIn("s_axis_tdata", {port.name for port in spec.inputs})
        self.assertNotIn("m_axis_tdata", {port.name for port in spec.outputs})
        self.assertEqual(spec.model_parameters["C_S_AXIS_TDATA_WIDTH"], 8)
        self.assertEqual(expected_transactions([{"tuser": 5, "tlast": 1}], p, spec.payload, spec.sink_payload),
                         [{"tuser": 5, "tlast": 1}])

    def test_bad_parameters_and_unconnected_modes_are_rejected(self):
        for changes in ({"input_bytes": True}, {"input_bytes": 513}, {"last_period": 257},
                {"output_user_width": 4097}, {"output_has_keep": False}, {"last_period": 3},
                {"input_has_last": False, "last_period": 3, "remap": {"tlast": "1'b1"}},
                {"remap": {"tid": "1'b0"}}, {"mapping": "unknown"}, {"remap": []}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                self.plugin.describe({**self.p, **changes})

    def test_mapping_cannot_generate_reserved_output_qualifiers(self):
        frame = dict(tdata=0, tuser=0, tstrb=7, tkeep=7, tlast=1)
        with self.assertRaisesRegex(ValueError, "保留"):
            self.expected({"remap": {"tkeep": "5'b00000", "tstrb": "5'b11111"}}, [frame])

    def test_no_input_data_only_allows_single_constant_output_data(self):
        p = {**self.p, "input_bytes": 0, "output_bytes": 3, "mapping": "resize",
             "input_has_keep": False, "input_has_strb": False}
        for remap in ({"tdata": "7'b0000000,tuser[16:0]"},
                      {"tdata": "8'b00000000,16'b0000000000000000"}):
            with self.assertRaisesRegex(PluginError, "单个二进制常量"):
                self.plugin.describe({**p, "remap": remap})
        spec = self.plugin.describe({**p, "remap": {"tdata": "24'b101001010101101001010101"}})
        self.assertEqual(spec.settings["TDATA_REMAP"], "24'b101001010101101001010101")

    def test_backend_uses_distinct_bus_widths_and_archives_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("axis_subset_converter", Path(directory))
            xci = Path(directory) / "fake.xci"
            xci.write_text("{}")
            spec = plugin.describe(case.parameters)
            with patch("vivado_ip_test.plugins.common.stream.testbench.load_metadata", return_value=(xci, {})):
                result = plugin.generate_testbench(case)
            self.assertEqual(len(result.input_path.read_text().splitlines()[0]), spec.width)
            self.assertEqual(len(result.expected_path.read_text().splitlines()[0]), sum(p.width for p in spec.sink_payload))
            self.assertEqual(result.metrics["prepared_additional_transfers"], 1 + sum(p.width * 2 for p in spec.generated_ports))
            manifest = json.loads(result.manifest_path.read_text())
            self.assertIn("expected_output", manifest["artifact_sha256"])
            schedule = json.loads(Path(manifest["artifacts"]["schedule"]).read_text())
            self.assertEqual(sorted(schedule["selected_vector_indices"]), list(range(case.verification.case_budget)))
            self.assertEqual(schedule["transaction_vector_indices"], list(range(result.vector_count)))
            def out_of_range(frames, *args):
                return [{**frame, "tdata": 1 << 40} for frame in frames]
            with patch("vivado_ip_test.plugins.common.stream.testbench.load_metadata", return_value=(xci, {})), \
                    patch("vivado_ip_test.plugins.axis_subset_converter.plugin.expected_transactions", side_effect=out_of_range):
                with self.assertRaisesRegex(ValueError, "invalid payload"):
                    plugin.generate_testbench(case)

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.domain import Stage, Status
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.axis_broadcaster.reference import expected_transactions
from vivado_ip_test.plugins.axis_broadcaster.remap import expression
from vivado_ip_test.plugins.axis_broadcaster.vectors import prepare_frames, ready_matrix
from unit.plugins.cycle_helpers import plugin_case


class BroadcasterTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axis_broadcaster")
        self.p = {**self.case.parameters, "branches": 3, "input_bytes": 3, "output_bytes": 4,
                  "input_user_width": 7, "output_user_width": 9}

    def test_data_and_user_modes_have_known_independent_results(self):
        frame = {"tdata": 0x123456, "tuser": 77, "tlast": 1}
        for mode, data in (("replicate", [0x123456] * 3),
                           ("rotate_bytes", [0x123456, 0x561234, 0x345612]),
                           ("reverse_alternate", [0x123456, 0x563412, 0x123456]),
                           ("constant_tag", [0x01010101, 0x02020202, 0x03030303])):
            p = {**self.p, "data_mapping": mode, "user_mapping": "rotate_bits"}
            result = expected_transactions([frame], p, self.plugin.describe(p))[0]
            self.assertEqual([result[f"m{i:02d}_tdata"] for i in range(3)], data)
            self.assertEqual([result[f"m{i:02d}_tuser"] for i in range(3)], [77, 102, 51])
            self.assertEqual([result[f"m{i:02d}_tlast"] for i in range(3)], [1] * 3)
        self.assertEqual(frame, {"tdata": 0x123456, "tuser": 77, "tlast": 1})

    def test_split_fields_and_branch_order(self):
        p = {**self.p, "output_bytes": 1, "input_user_width": 6, "output_user_width": 2,
             "data_mapping": "split", "user_mapping": "split"}
        spec = self.plugin.describe(p)
        row = expected_transactions([{"tdata": 0x332211, "tuser": 0b101011, "tlast": 0}], p, spec)[0]
        self.assertEqual([row[f"m{i:02d}_tdata"] for i in range(3)], [0x11, 0x22, 0x33])
        self.assertEqual([row[f"m{i:02d}_tuser"] for i in range(3)], [3, 2, 2])
        self.assertEqual([port.name for port in spec.sink_payload], list(row))
        self.assertEqual(spec.settings["M02_TDATA_REMAP"], "tdata[23:16]")

    def test_mapping_strings_use_correct_slice_and_zero_extension(self):
        self.assertEqual(expression("tdata", 24, 32, "rotate_bytes", 1),
                         "8'b00000000,tdata[7:0],tdata[23:8]")
        self.assertEqual(expression("tdata", 24, 24, "reverse_alternate", 1),
                         "tdata[7:0],tdata[15:8],tdata[23:16]")
        self.assertEqual(expression("tuser", 7, 9, "rotate_bits", 1), "2'b00,tuser[0],tuser[6:1]")
        self.assertEqual(expression("tdata", 0, 0, "replicate", 0), "1'b0")
        self.assertEqual(expression("tuser", 7, 2, "constant_tag", 4), "2'b01")

    def test_physical_ports_are_packed_by_branch_not_scalar(self):
        spec = self.plugin.describe(self.p)
        ports = {p.name: p for p in (*spec.inputs, *spec.outputs)}
        self.assertTrue(ports["s_axis_tlast"].scalar)
        self.assertFalse(ports["m_axis_tlast"].scalar)
        self.assertEqual(ports["m_axis_tdata"].width, 96)
        self.assertEqual(ports["m_axis_tready"].width, 3)
        p = {**self.p, "input_bytes": 0, "output_bytes": 0}
        ports = {port.name for port in (*self.plugin.describe(p).inputs, *self.plugin.describe(p).outputs)}
        self.assertNotIn("s_axis_tdata", ports)
        self.assertNotIn("m_axis_tdata", ports)

    def test_invalid_or_unconnected_parameters_rejected(self):
        for changes in ({"branches": 1}, {"branches": 17}, {"branches": True},
                        {"input_bytes": 513}, {"output_user_width": 4097}, {"has_keep": True},
                        {"output_bytes": 0}, {"data_mapping": "split"}, {"user_mapping": "split"},
                        {"input_user_width": 0}, {"data_mapping": "unknown"}, {"aclken": True}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                self.plugin.describe({**self.p, **changes})

    def test_every_branch_has_solo_and_blocked_ready_windows(self):
        profile = self.case.verification
        rows = ready_matrix(profile, 16)
        self.assertEqual(rows, ready_matrix(profile, 16))
        self.assertNotEqual(rows, ready_matrix(replace(profile, random_seed=987), 16))
        for b in range(16):
            self.assertIn(f"{1 << b:016b}", rows)
            self.assertIn(f"{65535 ^ (1 << b):016b}", rows)
        self.assertTrue(all(len(row) == 16 and set(row) <= {"0", "1"} for row in rows))

    def test_prefix_covers_walking_bits_and_preserves_tail(self):
        spec = self.plugin.describe(self.p)
        tail = [{port.name: port.limit for port in spec.payload}]
        frames = prepare_frames(tail, spec)
        self.assertEqual(frames[-1:], tail)
        self.assertIsNot(frames[-1], tail[0])
        for port in spec.generated_ports:
            values = {frame[port.name] for frame in frames}
            for bit in range(port.width):
                self.assertIn(1 << bit, values)
                self.assertIn(port.limit ^ (1 << bit), values)

    def test_backend_archives_grouped_output_and_audits_actual_input(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("axis_broadcaster", Path(directory))
            xci = Path(directory) / "fake.xci"
            xci.write_text("{}")
            with patch("vivado_ip_test.plugins.common.stream.testbench.load_metadata", return_value=(xci, {})):
                result = plugin.generate_testbench(case)
            spec = plugin.describe(case.parameters)
            self.assertEqual(result.metrics["output_branch_count"], 2)
            self.assertEqual(result.metrics["backpressure_pattern"], "broadcaster_independent_windows:1.0")
            self.assertEqual(result.metrics["checked_output_transfers"], 2 * result.vector_count)
            self.assertEqual(len(result.expected_path.read_text().splitlines()[0]), sum(p.width for p in spec.sink_payload))
            manifest = json.loads(result.manifest_path.read_text())
            self.assertEqual(len(Path(manifest["artifacts"]["ready"]).read_text().splitlines()[0]), 2)
            text = result.testbench_path.read_text()
            self.assertIn("received(b) < offered", text)
            self.assertNotIn("received <= sent", text)
            result.actual_path.write_bytes(result.expected_path.read_bytes())
            accepted = Path(manifest["artifacts"]["accepted_input"])
            accepted.write_bytes(result.input_path.read_bytes())
            self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.PASS)
            accepted.write_text("0\n")
            self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.VERIFICATION_FAILED)

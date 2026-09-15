from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.domain import Stage, Status
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.axis_switch.reference import expected_transactions, route_for_destination
from vivado_ip_test.plugins.axis_switch.testbench import write_vectors
from vivado_ip_test.plugins.axis_switch.vectors import prepare_frames, source_schedules, ready_matrix, routing_prefix_groups
from unit.plugins.cycle_helpers import plugin_case


class SwitchTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axis_switch")
        self.p = {**self.case.parameters, "inputs": 3, "outputs": 3, "output_reg": True}

    def test_route_ranges_and_known_boundaries(self):
        spec = self.plugin.describe(self.p)
        self.assertEqual(spec.routes, ((0, 1), (2, 4), (5, 7)))
        self.assertEqual([route_for_destination(d, spec.routes) for d in range(8)], [0, 0, 1, 1, 1, 2, 2, 2])
        self.assertEqual(self.plugin.describe({**self.p, "routing": "reversed"}).routes, ((5, 7), (2, 4), (0, 1)))
        self.assertEqual(self.plugin.describe({**self.p, "routing": "gapped"}).routes, ((0, 0), (2, 2), (4, 4)))
        self.assertEqual(spec.settings["M01_AXIS_HIGHTDEST"], "0x00000004")
        self.assertEqual(int(spec.model_parameters["C_M_AXIS_BASETDEST_ARRAY"], 2), 5*64+2*8)
        for value, routes in ((8, spec.routes), (1, ((0, 2), (1, 3)))):
            with self.assertRaises(ValueError):
                route_for_destination(value, routes)

    def test_reference_keeps_every_payload_and_adds_independent_route(self):
        spec = self.plugin.describe(self.p)
        frame = {p.name: p.limit for p in spec.payload}
        frame.update(s00_tdest=1, s01_tdest=4, s02_tdest=7)
        expected = expected_transactions([frame], spec)[0]
        self.assertEqual([expected[f"s{i:02d}_route"] for i in range(3)], [0, 1, 2])
        self.assertEqual({k: v for k, v in expected.items() if not k.endswith("_route")}, frame)
        expected["s00_tdata"] = 0
        self.assertNotEqual(expected["s00_tdata"], frame["s00_tdata"])

    def test_scalar_clock_but_vector_handshakes_even_for_one_port(self):
        spec = self.plugin.describe(self.case.parameters)
        ports = {p.name: p for p in (*spec.inputs, *spec.outputs)}
        self.assertTrue(ports["aclk"].scalar)
        self.assertFalse(ports["s_axis_tvalid"].scalar)
        self.assertEqual(ports["s_axis_tvalid"].width, 1)
        self.assertEqual(ports["m_axis_tdata"].width, 72)
        self.assertNotIn("s_req_suppress", ports)
        spec = self.plugin.describe({**self.p, "outputs": 1, "decoder_reg": False})
        self.assertEqual({p.name: p.width for p in spec.inputs}["s_req_suppress"], 3)

    def test_reserved_tags_are_excluded_from_generated_bit_widths(self):
        spec = self.plugin.describe(self.p)
        self.assertEqual((spec.tag_field, spec.tag_bits), ("tdata", 2))
        numeric = {p.name: p.width for p in spec.generated_ports}
        self.assertEqual(numeric["s00_tdata"], 22)
        self.assertNotIn("s00_tdest", numeric)
        self.assertNotIn("s00_tlast", numeric)
        for changes, field in (({"data_bytes": 0, "has_keep": False, "has_strb": False}, "tuser"),
                               ({"data_bytes": 0, "has_keep": False, "has_strb": False, "user_width": 0}, "tid")):
            self.assertEqual(self.plugin.describe({**self.p, **changes}).tag_field, field)

    def test_invalid_and_normalized_parameters_fail_before_tools(self):
        for changes in ({"inputs": 0}, {"outputs": 17}, {"inputs": True}, {"dest_width": 1},
                        {"inputs": 1}, {"outputs": 1}, {"data_bytes": 0}, {"user_width": 4097},
                        {"arbiter": "external"}, {"routing": "invalid"}, {"arbitrate_transfers": 0},
                        {"arbitrate_transfers": 7}, {"has_last": False, "arbitrate_last": True},
                        {"decoder_reg": 1}, {"suppress_requests": True}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                self.plugin.describe({**self.p, **changes})

    def test_packet_routes_are_constant_until_last_and_finish_cleanly(self):
        spec = self.plugin.describe({**self.p, "arbitrate_transfers": 0, "arbitrate_last": True})
        rows = prepare_frames([{p.name: 1 for p in spec.generated_ports}], spec)
        for lane in range(3):
            previous, last = None, True
            for row in rows:
                dest = row[f"s{lane:02d}_tdest"]
                if not last:
                    self.assertEqual(dest, previous)
                previous, last = dest, bool(row[f"s{lane:02d}_tlast"])
                self.assertEqual(row[f"s{lane:02d}_tdata"] & 3, lane)
            self.assertTrue(last)
        self.assertEqual(set(route_for_destination(row["s00_tdest"], spec.routes) for row in rows), {0, 1, 2})

    def test_transfer_quota_is_padded_and_bit_prefix_is_preserved(self):
        spec = self.plugin.describe({**self.p, "arbitrate_transfers": 7, "arbitrate_cycles": 3})
        rows = prepare_frames([], spec)
        self.assertEqual(len(rows) % 7, 0)
        for port in spec.generated_ports:
            lane = int(port.name[1:3])
            shift = spec.tag_bits if port.name.endswith("_" + spec.tag_field) else 0
            values = {row[port.name] >> shift for row in rows}
            for bit in range(port.width):
                self.assertIn(1 << bit, values)
                self.assertIn(port.limit ^ (1 << bit), values)

    def test_source_and_sink_schedules_are_independent_and_repeatable(self):
        first = source_schedules(100, self.case.verification, 3)
        self.assertEqual(first, source_schedules(100, self.case.verification, 3))
        self.assertEqual(len({s.gaps for s in first}), 3)
        ready = ready_matrix(self.case.verification, 3)
        self.assertEqual(ready, ready_matrix(self.case.verification, 3))
        for value in ("001", "010", "100", "110", "101", "011", "111"):
            self.assertIn(value, ready)

    def test_tiny_numeric_space_still_visits_every_route_and_boundary(self):
        parameters = {**self.case.parameters, "inputs": 1, "outputs": 8,
            "data_bytes": 0, "user_width": 1, "id_width": 0, "dest_width": 32,
            "has_keep": False, "has_strb": False, "routing": "reversed"}
        for lanes, packet_mode, width in ((1, False, 1), (3, True, 3)):
            spec = self.plugin.describe({**parameters, "inputs": lanes,
                "user_width": width, "arbitrate_last": packet_mode})
            samples = [{p.name: value for p in spec.generated_ports} for value in (0, 1)]
            frames = prepare_frames(samples, spec)
            self.assertEqual(samples, [{p.name: value for p in spec.generated_ports} for value in (0, 1)])
            self.assertGreaterEqual(len(frames), routing_prefix_groups(spec))
            for lane in range(lanes):
                destinations = {row[f"s{lane:02d}_tdest"] for row in frames}
                for low, high in spec.routes:
                    self.assertTrue({low, high, (low+high)//2} <= destinations)
                self.assertTrue(frames[-1][f"s{lane:02d}_tlast"])

    def test_large_quota_preserves_complete_contention_and_spread_prefix(self):
        spec = self.plugin.describe({**self.p, "data_bytes": 1, "user_width": 0,
            "id_width": 0, "has_keep": False, "has_strb": False,
            "arbitrate_transfers": 1024, "arbitrate_cycles": 3})
        rows = prepare_frames([], spec)
        self.assertEqual(len(rows), 7 * 3 * 1024)
        for lane in range(3):
            destinations = [row[f"s{lane:02d}_tdest"] for row in rows]
            for start in range(0, len(rows), 1024):
                self.assertEqual(len(set(destinations[start:start+1024])), 1)
            spread = destinations[4*3*1024:]
            self.assertEqual({route_for_destination(d, spec.routes) for d in spread}, {0, 1, 2})

    def test_backend_archives_stream_mapping_and_checks_input_and_output(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("axis_switch", Path(directory))
            case = replace(case, parameters=self.p)
            xci = Path(directory) / "fake.xci"
            xci.write_text("{}")
            with patch("vivado_ip_test.plugins.axis_switch.testbench.load_metadata", return_value=(xci, {})):
                result = plugin.generate_testbench(case)
            manifest = json.loads(result.manifest_path.read_text())
            paths = {k: Path(v) for k, v in manifest["artifacts"].items()}
            schedule = json.loads(paths["schedule"].read_text())
            self.assertEqual(result.vector_count, result.metrics["input_groups"] * 3)
            self.assertEqual(len(schedule["output_mapping"]), result.vector_count)
            self.assertEqual(len(schedule["gaps_by_input_lane"]), 3)
            self.assertEqual(result.expected_path.read_bytes(), b"".join(
                paths[f"expected_{s}_{b}"].read_bytes() for s in range(3) for b in range(3)))
            for name, digest in manifest["artifact_sha256"].items():
                self.assertEqual(sha256_file(paths[name]), digest)
            text = result.testbench_path.read_text()
            self.assertIn("received(s)(b) <= sent(s)(b)", text)
            self.assertIn("file_open(actual_2_2", text)
            self.assertIn("input_events_2", paths)
            result.actual_path.write_bytes(result.expected_path.read_bytes())
            paths["accepted_input"].write_bytes(result.input_path.read_bytes())
            self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.PASS)
            paths["accepted_input"].write_text("0\n")
            self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.VERIFICATION_FAILED)
            with patch("vivado_ip_test.plugins.axis_switch.testbench.load_metadata", return_value=(xci, {})):
                plugin.generate_testbench(case)
            self.assertFalse(result.actual_path.exists())

    def test_bad_shape_tag_and_timing_are_rejected(self):
        spec = self.plugin.describe(self.p)
        frames = prepare_frames([], spec)[:2]
        expected = expected_transactions(frames, spec)
        schedules = source_schedules(2, self.case.verification, 3)
        changes = [([], expected, schedules), (frames, expected[:1], schedules),
            ([{**frames[0], "s00_tdata": 1}, frames[1]], expected, schedules),
            ([{**frames[0], "s00_tdata": 1 << 24}, frames[1]], expected, schedules),
            (frames, expected, schedules[:1]),
            (frames, expected, [replace(schedules[0], gaps=(-1, 0)), *schedules[1:]])]
        with tempfile.TemporaryDirectory() as directory:
            for f, e, s in changes:
                with self.subTest(frames=len(f), schedules=len(s)), self.assertRaises(ValueError):
                    write_vectors(Path(directory), spec, f, e, s, self.case.verification)

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.domain import Stage, Status
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.axis_combiner.reference import expected_transactions
from vivado_ip_test.plugins.axis_combiner.vectors import prepare_frames, lane_gaps
from vivado_ip_test.services.stimulus_schedule import build_schedule
from unit.plugins.cycle_helpers import plugin_case


class CombinerTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axis_combiner")
        self.p = {**self.case.parameters, "inputs": 3, "user_width": 3,
                  "id_width": 2, "dest_width": 3, "primary_input": 2,
                  "has_keep": True, "has_strb": True}

    def test_concat_lane_zero_is_low_and_primary_fields_are_selected(self):
        frame = {}
        for lane, data, user, last, ident, dest in (
                (0, 0x11, 1, 0, 1, 3), (1, 0x22, 3, 0, 2, 4), (2, 0x33, 5, 1, 3, 7)):
            frame.update({f"s{lane:02d}_{k}": v for k, v in dict(
                tdata=data, tuser=user, tlast=last, tid=ident, tdest=dest, tkeep=lane % 2, tstrb=1-lane % 2).items()})
        original = dict(frame)
        for primary in range(3):
            spec = self.plugin.describe({**self.p, "primary_input": primary})
            result = expected_transactions([frame], spec)[0]
            self.assertEqual(result, dict(tdata=0x332211, tuser=0b101011001,
                tlast=[0, 0, 1][primary], tid=[1, 2, 3][primary], tdest=[3, 4, 7][primary],
                tkeep=0b010, tstrb=0b101))
        self.assertEqual(frame, original)

    def test_physical_input_and_output_widths_differ_for_primary_fields(self):
        spec = self.plugin.describe(self.p)
        ports = {p.name: p for p in (*spec.inputs, *spec.outputs)}
        self.assertEqual(ports["s_axis_tvalid"].width, 3)
        self.assertEqual(ports["s_axis_tid"].width, 6)
        self.assertEqual(ports["m_axis_tid"].width, 2)
        self.assertEqual(ports["m_axis_tuser"].width, 9)
        self.assertFalse(ports["s_axis_tlast"].scalar)
        self.assertTrue(ports["m_axis_tlast"].scalar)
        self.assertEqual(spec.model_parameters["C_MASTER_PORT_NUM"], 2)

    def test_sideband_only_and_widest_user_are_not_capped_by_data_width(self):
        spec = self.plugin.describe({**self.p, "inputs": 16, "data_bytes": 0,
                                    "user_width": 4096, "has_keep": False, "has_strb": False})
        ports = {p.name: p for p in (*spec.inputs, *spec.outputs)}
        self.assertNotIn("s_axis_tdata", ports)
        self.assertEqual(ports["m_axis_tuser"].width, 65536)

    def test_invalid_parameters_are_rejected(self):
        for change in ({"inputs": 1}, {"inputs": 17}, {"inputs": True}, {"primary_input": 3},
                       {"data_bytes": 171}, {"data_bytes": 0}, {"user_width": 4097},
                       {"id_width": 33}, {"dest_width": 33}, {"has_last": 1}, {"cmd_err": True},
                       {"has_last": False, "id_width": 0, "dest_width": 0}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                self.plugin.describe({**self.p, **change})

    def test_prefix_isolates_every_lane_bit_and_differentiates_packet_ends(self):
        spec = self.plugin.describe(self.p)
        numerical = {p.name: 0 for p in spec.generated_ports}
        rows = prepare_frames([numerical], spec)
        for port in spec.generated_ports:
            for bit in range(port.width):
                self.assertTrue(any(row[port.name] == 1 << bit and all(
                    row[p.name] == 0 for p in spec.generated_ports if p.name != port.name) for row in rows))
                self.assertIn(port.limit ^ (1 << bit), {row[port.name] for row in rows})
        self.assertTrue(all(rows[-1][f"s{i:02d}_tlast"] == 1 for i in range(3)))
        self.assertTrue(any(len({row[f"s{i:02d}_tlast"] for i in range(3)}) > 1 for row in rows))
        self.assertNotIn("s00_tlast", numerical)

    def test_independent_gaps_have_each_lane_first_and_last(self):
        profile = self.case.verification
        schedule = build_schedule(100, profile, can_idle=True)
        rows = lane_gaps(schedule, profile, 16)
        self.assertEqual(rows, lane_gaps(schedule, profile, 16))
        self.assertNotEqual(rows, lane_gaps(schedule, replace(profile, random_seed=8), 16))
        for lane in range(16):
            self.assertGreater(rows[lane][lane], max(v for i, v in enumerate(rows[lane]) if i != lane))
            self.assertLess(rows[16+lane][lane], min(v for i, v in enumerate(rows[16+lane]) if i != lane))
        self.assertEqual(lane_gaps(schedule, replace(profile, timing_mode="continuous"), 16), [[0]*16]*100)

    def test_backend_records_lane_schedule_and_checks_accepted_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("axis_combiner", Path(directory))
            xci = Path(directory) / "fake.xci"
            xci.write_text("{}")
            with patch("vivado_ip_test.plugins.common.stream.testbench.load_metadata", return_value=(xci, {})):
                result = plugin.generate_testbench(case)
            manifest = json.loads(result.manifest_path.read_text())
            schedule = json.loads(Path(manifest["artifacts"]["schedule"]).read_text())
            gaps = [[int(v) for v in row.split()] for row in Path(manifest["artifacts"]["gaps"]).read_text().splitlines()]
            self.assertEqual(gaps, schedule["gaps_by_lane"])
            self.assertEqual([max(row) for row in gaps], schedule["gaps_before_vector"])
            self.assertTrue(all(len(row) == 2 for row in gaps))
            self.assertEqual(result.metrics["checked_input_transfers"], result.vector_count * 2)
            self.assertEqual(result.metrics["checked_output_transfers"], result.vector_count)
            self.assertEqual(result.metrics["source_timing_pattern"], "combiner_independent_inputs:1.0")
            self.assertIn("received <= sent(b)", result.testbench_path.read_text())
            result.actual_path.write_bytes(result.expected_path.read_bytes())
            accepted = Path(manifest["artifacts"]["accepted_input"])
            accepted.write_bytes(result.input_path.read_bytes())
            self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.PASS)
            accepted.write_text("0\n")
            self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.VERIFICATION_FAILED)

    def test_bad_lane_timing_is_rejected(self):
        for bad in ([], [[0]], [[-1, 0]], [[True, 0]]):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as directory:
                plugin, case = plugin_case("axis_combiner", Path(directory))
                xci = Path(directory) / "fake.xci"
                xci.write_text("{}")
                def timing(schedule, profile, lanes):
                    return bad * len(schedule.gaps)
                with patch("vivado_ip_test.plugins.common.stream.testbench.load_metadata", return_value=(xci, {})), \
                     patch("vivado_ip_test.plugins.axis_combiner.plugin.lane_gaps", side_effect=timing), \
                     self.assertRaisesRegex(ValueError, "invalid input gaps"):
                    plugin.generate_testbench(case)

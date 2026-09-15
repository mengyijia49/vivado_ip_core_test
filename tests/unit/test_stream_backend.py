from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.domain import Stage, Status
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.stream.testbench import packetize, ready_pattern, render_testbench
from vivado_ip_test.services.stimulus_schedule import build_schedule
from unit.plugins.cycle_helpers import ROOT, plugin_case


class StreamBackendTests(unittest.TestCase):
    def test_packet_boundaries_survive_shuffled_input(self):
        plugin, case = plugin_case("axis_data_fifo")
        spec = plugin.describe(case.parameters)
        vectors = tuple((index,) * len(spec.generated_ports) for index in range(100))
        schedule = build_schedule(len(vectors), replace(case.verification, input_order="shuffled"), can_idle=True)
        frames = packetize(spec, vectors, schedule)
        self.assertEqual([f["tdata"] for f in frames], list(schedule.transaction_indices))
        endings = [i + 1 for i, f in enumerate(frames) if f["tlast"]]
        lengths = [end - start for start, end in zip([0, *endings], endings)]
        self.assertEqual(lengths[:8], [1, 2, 3, 7, 16, 15, 16, 17])
        self.assertEqual(frames[-1]["tlast"], 1)
        self.assertTrue(all(f["tkeep"] == 15 and f["tstrb"] == 15 for f in frames))

    def test_file_generation_and_post_simulation_input_audit(self):
        for ip_type in ("axis_register_slice", "axis_data_fifo", "axis_clock_converter"):
            with self.subTest(ip_type=ip_type), tempfile.TemporaryDirectory() as directory:
                plugin, case = plugin_case(ip_type, Path(directory))
                xci = Path(directory) / "fixture.xci"
                xci.write_text("{}")
                with patch("vivado_ip_test.plugins.common.stream.testbench.load_metadata", return_value=(xci, {})):
                    a = plugin.generate_testbench(case)
                    first = a.testbench_path.read_bytes()
                    b = plugin.generate_testbench(case)
                self.assertEqual(first, b.testbench_path.read_bytes())
                self.assertEqual(a.input_path.read_text(), a.expected_path.read_text())
                manifest = json.loads(a.manifest_path.read_text())
                self.assertIn("ready", manifest["artifact_sha256"])
                self.assertIn("accepted_input", manifest["artifacts"])
                self.assertEqual(a.metrics["simulation_mode"], "behavioral")
                gaps = Path(manifest["artifacts"]["gaps"]).read_text().splitlines()
                schedule = json.loads(Path(manifest["artifacts"]["schedule"]).read_text())
                self.assertEqual([int(row) for row in gaps], schedule["gaps_before_vector"])
                self.assertNotIn("gaps_by_lane", schedule)
                self.assertEqual(a.metrics["input_lane_count"], 1)
                self.assertEqual(a.metrics["checked_input_transfers"], a.vector_count)
                self.assertFalse(a.actual_path.exists())
                self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.VERIFICATION_FAILED)
                a.actual_path.write_bytes(a.expected_path.read_bytes())
                self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.VERIFICATION_FAILED)
                accepted = Path(manifest["artifacts"]["accepted_input"])
                accepted.write_bytes(a.input_path.read_bytes())
                self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.PASS)
                accepted.write_text("X\n")
                self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.VERIFICATION_FAILED)

    def test_reference_does_not_mutate_inputs(self):
        for name in ("axis_register_slice", "axis_data_fifo", "axis_clock_converter"):
            plugin, _ = plugin_case(name)
            frames = [{"tdata": 255, "tlast": 1}, {"tdata": 0, "tlast": 0}]
            output = plugin.expected_transactions(frames)
            self.assertEqual(output, frames)
            output[0]["tdata"] = 7
            self.assertEqual(frames[0]["tdata"], 255)

    def test_ready_pattern_is_seeded_separately_and_contains_progress(self):
        _, case = plugin_case("axis_register_slice")
        pattern = ready_pattern(case.verification)
        self.assertEqual(pattern, ready_pattern(case.verification))
        self.assertNotEqual(pattern, ready_pattern(replace(case.verification, random_seed=7)))
        self.assertEqual(pattern[:8], [0] * 8)
        self.assertEqual(pattern[-32:], [1] * 32)

    def test_invalid_fifo_or_budget_rejected_before_tools(self):
        plugin, case = plugin_case("axis_data_fifo")
        for change in ({"depth": 17}, {"packet_mode": True, "has_last": False},
                       {"synchronization_stages": 9}, {"synchronization_stages": 2},
                       {"data_bytes": True}, {"memory_type": "ultra"}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                plugin.validate_case(replace(case, parameters={**case.parameters, **change}))
        with self.assertRaises(PluginError):
            plugin.validate_case(replace(case, verification=replace(case.verification, case_budget=1)))

    def test_clock_domains_and_handshake_checks_are_explicit(self):
        plugin, case = plugin_case("axis_clock_converter")
        spec = plugin.describe(case.parameters)
        self.assertEqual(spec.output_period_ns, 14)
        self.assertIn("m_axis_aresetn", [p.name for p in spec.inputs])
        names = ("input_vectors", "gaps", "ready", "accepted_input", "expected_output",
                 "actual_output", "protocol_events", "protocol_summary")
        paths = {name: Path("/tmp") / name for name in names}
        text = render_testbench(spec, paths, 10, 8, 100)
        self.assertIn("m_clk <= not m_clk after 7 ns", text)
        self.assertIn("exit when s_ready = '1'", text)
        self.assertIn("output changed under backpressure", text)
        self.assertIn("received <= sent", text)
        self.assertIn("extra output", text)
        self.assertIn("watchdog timeout", text)
        self.assertIn("drain_cycles = 64", text)

    def test_only_behavioral_simulation_is_in_scope(self):
        self.assertEqual({stage.value for stage in Stage},
                         {"create_ip", "sim_demo", "generate_testbench", "sim_selfcheck"})
        sim = (ROOT / "tcl/run_xsim_batch.tcl").read_text()
        self.assertIn("-mode behavioral -scripts_only", sim)
        for path in (ROOT / "tcl").rglob("*.tcl"):
            text = path.read_text()
            for command in ("synth_design", "launch_runs", "opt_design", "place_design", "route_design"):
                self.assertNotIn(command, text, str(path))

    def test_each_stream_schema_is_referenced_by_its_own_ip_type(self):
        schema = json.loads((ROOT / "configs/schemas/ip_matrix.schema.json").read_text())
        rules = schema["$defs"]["case_fields"]["allOf"]
        refs = {r["if"]["properties"]["ip_type"]["const"]:
                r["then"]["properties"]["parameters"]["$ref"] for r in rules}
        for name in ("axis_register_slice", "axis_data_fifo", "axis_clock_converter"):
            self.assertEqual(refs[name], f"ip/{name}/parameters.schema.json")

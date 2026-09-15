from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout
from vivado_ip_test.plugins.axis_combiner.plugin import AxisCombinerPlugin
from vivado_ip_test.plugins.axis_combiner.testbench import render_testbench
from vivado_ip_test.plugins.common.testbench import packed
from vivado_ip_test.strategies import create_default_strategy_registry


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class CombinerFailureDetectionTests(unittest.TestCase):
    def test_correct_independent_inputs(self):
        self.run_fault(0, "control", "AXIS_SELF_CHECK_STATUS: PASS")

    def test_output_requires_all_inputs(self):
        self.run_fault(1, "early_valid", "output before all inputs offered")

    def test_swapped_data_lanes(self):
        self.run_fault(2, "swapped_data", "payload mismatch")

    def test_wrong_primary_last(self):
        self.run_fault(3, "primary_last", "payload mismatch")

    def test_wrong_primary_id(self):
        self.run_fault(4, "primary_id", "payload mismatch")

    def test_wrong_primary_dest(self):
        self.run_fault(5, "primary_dest", "payload mismatch")

    def test_swapped_user_lanes(self):
        self.run_fault(6, "swapped_user", "payload mismatch")

    def test_output_changes_under_stall(self):
        self.run_fault(7, "unstable", "output changed under backpressure")

    def test_unknown_valid(self):
        self.run_fault(8, "unknown_valid", "unknown output valid")

    def test_missing_output_times_out(self):
        self.run_fault(9, "missing", "watchdog timeout")

    def test_output_requires_every_input_handshake(self):
        self.run_fault(10, "missing_input_ack", "output before all input handshakes")

    def test_unknown_input_ready(self):
        self.run_fault(11, "unknown_ready", "unknown input ready")

    def run_fault(self, mode, name, marker):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        plugin = AxisCombinerPlugin(layout, create_default_strategy_registry())
        p = dict(inputs=2, data_bytes=1, user_width=4, id_width=2, dest_width=3,
                 has_keep=False, has_strb=False, has_last=True, primary_input=1)
        spec = plugin.describe(p)
        run = root / "runs/framework/failure_detection" / layout.run_id / "axis_combiner" / name
        logs = root / "runs/logs/framework/failure_detection" / layout.run_id / "axis_combiner" / name
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        paths = {key: run / f"{key}.txt" for key in (
            "input_vectors", "expected_output", "actual_output", "gaps", "ready",
            "accepted_input", "protocol_events", "protocol_summary")}
        frames, expected = [], []
        for index in range(8):
            low = dict(tdata=0x12+index, tuser=1+index, tid=0, tdest=1, tlast=0)
            high = dict(tdata=0x81+index, tuser=15-index, tid=3, tdest=7, tlast=1)
            frames.append({**{f"s00_{k}": v for k, v in low.items()},
                           **{f"s01_{k}": v for k, v in high.items()}})
            expected.append(dict(tdata=(0x81+index)*256+0x12+index,
                                 tuser=(15-index)*16+1+index, tid=3, tdest=7, tlast=1))
        for key, rows, ports in (("input_vectors", frames, spec.payload),
                                  ("expected_output", expected, spec.sink_payload)):
            paths[key].write_text("".join(packed(row, ports) + "\n" for row in rows))
        paths["gaps"].write_text("8 0\n0 8\n3 1\n0 0\n4 0\n0 4\n2 0\n0 0\n")
        paths["ready"].write_text("1\n1\n0\n0\n0\n1\n1\n1\n")
        testbench = run / "tb_stream_selfcheck.vhd"
        text = render_testbench(spec, paths, len(frames), 8, 20)
        testbench.write_text(text.replace("port map (", f"generic map (fault_mode => {mode})\n    port map (", 1))
        runner = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = runner.run(description="Create combiner checker fixture:",
                source=root / "tests/fixtures/create_testbench_project.tcl",
                tclargs=[str(run), str(root / "tests/fixtures/ip/axis_combiner/faulty_combiner.vhd")],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            result = runner.run(description="Run combiner checker fixture:", source=root / "tcl/run_xsim_batch.tcl",
                tclargs=[str(run / "proj/framework_negative.xpr"), str(testbench), "tb_stream_selfcheck",
                         "AXIS_SELF_CHECK_STATUS: PASS", "AXIS_SELF_CHECK_STATUS: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
        self.assertEqual(result.returncode, 0 if mode == 0 else 1, result.output[-3000:])
        self.assertRegex(result.output, marker)
        if mode == 0:
            self.assertEqual(paths["actual_output"].read_bytes(), paths["expected_output"].read_bytes())
            self.assertEqual(paths["accepted_input"].read_bytes(), paths["input_vectors"].read_bytes())
            summary = paths["protocol_summary"].read_text()
            self.assertRegex(summary, r"partial_input_cycles=[1-9]")
            self.assertRegex(summary, r"output_stall_cycles=[1-9]")

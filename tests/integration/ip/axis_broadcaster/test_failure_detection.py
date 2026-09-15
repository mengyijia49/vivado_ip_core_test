from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout
from vivado_ip_test.plugins.axis_broadcaster.plugin import AxisBroadcasterPlugin
from vivado_ip_test.plugins.axis_broadcaster.testbench import render_testbench
from vivado_ip_test.plugins.common.testbench import packed
from vivado_ip_test.strategies import create_default_strategy_registry


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class BroadcasterFailureDetectionTests(unittest.TestCase):
    def test_correct_independent_handshakes(self):
        self.run_fault(0, "control", "AXIS_SELF_CHECK_STATUS: PASS")

    def test_repeated_branch_is_rejected(self):
        self.run_fault(1, "duplicate", "output before offered input|duplicate branch")

    def test_missing_branch_times_out(self):
        self.run_fault(2, "missing", "watchdog timeout")

    def test_incorrect_data_mapping(self):
        self.run_fault(3, "data", "payload mismatch branch=1")

    def test_backpressured_branch_must_hold_data(self):
        self.run_fault(4, "unstable", "output changed under backpressure")

    def test_incorrect_user_mapping(self):
        self.run_fault(5, "user", "payload mismatch branch=1")

    def test_unknown_valid(self):
        self.run_fault(6, "unknown", "unknown output valid")

    def test_output_without_offered_input(self):
        self.run_fault(7, "phantom", "output before offered input")

    def test_input_accepted_without_preserving_blocked_outputs(self):
        self.run_fault(8, "premature_ready", "output changed under backpressure")

    def run_fault(self, mode, name, marker):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        plugin = AxisBroadcasterPlugin(layout, create_default_strategy_registry())
        p = {"branches": 2, "input_bytes": 2, "output_bytes": 2,
             "input_user_width": 8, "output_user_width": 8, "id_width": 0, "dest_width": 0,
             "has_keep": False, "has_strb": False, "has_last": True,
             "data_mapping": "rotate_bytes", "user_mapping": "rotate_bits"}
        spec = plugin.describe(p)
        run = root / "runs/framework/failure_detection" / layout.run_id / "axis_broadcaster" / name
        logs = root / "runs/logs/framework/failure_detection" / layout.run_id / "axis_broadcaster" / name
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        paths = {key: run / f"{key}.txt" for key in (
            "input_vectors", "expected_output", "actual_output", "gaps", "ready",
            "accepted_input", "protocol_events", "protocol_summary")}
        values = [(0x1234, 0x81, 0), (0x5678, 0x93, 1), (0, 255, 0), (65535, 0, 0),
                  (0x8001, 1, 1), (0xAA55, 0x5A, 1), (0x0307, 9, 0), (0x0102, 0x80, 1)]
        frames = [dict(tdata=d, tuser=u, tlast=last) for d, u, last in values]
        expected = [dict(m00_tdata=d, m00_tuser=u, m00_tlast=last,
                         m01_tdata=(d % 256) * 256 + d // 256,
                         m01_tuser=u // 2 + (u % 2) * 128, m01_tlast=last) for d, u, last in values]
        for key, rows, ports in (("input_vectors", frames, spec.payload),
                                  ("expected_output", expected, spec.sink_payload)):
            paths[key].write_text("".join(packed(row, ports) + "\n" for row in rows))
        paths["gaps"].write_text("5\n3\n1\n0\n4\n0\n2\n0\n")
        paths["ready"].write_text("10\n10\n10\n11\n01\n01\n11\n00\n11\n")
        testbench = run / "tb_stream_selfcheck.vhd"
        text = render_testbench(spec, paths, len(frames), 5, 0 if mode == 7 else 20)
        testbench.write_text(text.replace("port map (", f"generic map (fault_mode => {mode})\n    port map (", 1))
        runner = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = runner.run(description="Create broadcaster checker fixture:",
                source=root / "tests/fixtures/create_testbench_project.tcl",
                tclargs=[str(run), str(root / "tests/fixtures/ip/axis_broadcaster/faulty_broadcaster.vhd")],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            result = runner.run(description="Run broadcaster checker fixture:", source=root / "tcl/run_xsim_batch.tcl",
                tclargs=[str(run / "proj/framework_negative.xpr"), str(testbench), "tb_stream_selfcheck",
                         "AXIS_SELF_CHECK_STATUS: PASS", "AXIS_SELF_CHECK_STATUS: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
        self.assertEqual(result.returncode, 0 if mode == 0 else 1, result.output[-3000:])
        self.assertRegex(result.output, marker)
        if mode == 0:
            self.assertEqual(paths["actual_output"].read_bytes(), paths["expected_output"].read_bytes())
            self.assertEqual(paths["accepted_input"].read_bytes(), paths["input_vectors"].read_bytes())
            self.assertRegex(paths["protocol_summary"].read_text(), r"early_handshakes=[1-9]")

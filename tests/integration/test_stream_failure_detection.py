from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout
from vivado_ip_test.plugins.axis_register_slice.plugin import AxisRegisterSlicePlugin
from vivado_ip_test.plugins.common.stream.testbench import render_testbench
from vivado_ip_test.strategies import create_default_strategy_registry


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class StreamFailureDetectionTests(unittest.TestCase):
    def test_transparent_control(self):
        self.run_fault(0, "control", "AXIS_SELF_CHECK_STATUS: PASS")

    def test_unknown_payload(self):
        self.run_fault(1, "unknown", "output changed under backpressure")

    def test_unstable_payload(self):
        self.run_fault(2, "unstable", "output changed under backpressure")

    def test_extra_output(self):
        self.run_fault(3, "extra", "extra output")

    def test_dropped_output(self):
        self.run_fault(4, "drop", "watchdog timeout")

    def test_corrupted_output(self):
        self.run_fault(5, "corrupt", "payload mismatch")

    def run_fault(self, mode, name, marker):
        root = Path(__file__).resolve().parents[2]
        layout = RepositoryLayout(root)
        plugin = AxisRegisterSlicePlugin(layout, create_default_strategy_registry())
        spec = plugin.describe({"data_bytes": 1, "id_width": 0, "dest_width": 0, "user_width": 0,
            "has_last": False, "has_keep": False, "has_strb": False, "register_mode": "Bypass"})
        run = root / "runs/framework/failure_detection" / layout.run_id / "axis_register_slice" / name
        logs = root / "runs/logs/framework/failure_detection" / layout.run_id / "axis_register_slice" / name
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        paths = {key: run / f"{key}.txt" for key in (
            "input_vectors", "expected_output", "actual_output", "gaps", "ready",
            "accepted_input", "protocol_events", "protocol_summary")}
        paths["input_vectors"].write_text("00000000\n00000001\n01010101\n11111111\n")
        paths["expected_output"].write_bytes(paths["input_vectors"].read_bytes())
        paths["gaps"].write_text("0\n0\n0\n0\n")
        paths["ready"].write_text("1\n1\n0\n1\n")
        testbench = run / "tb_stream_selfcheck.vhd"
        text = render_testbench(spec, paths, 4, 2, 20)
        testbench.write_text(text.replace("port map (", f"generic map (fault_mode => {mode})\n    port map (", 1))
        runner = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = runner.run(description="Create stream checker fixture:",
                source=root / "tests/fixtures/create_testbench_project.tcl",
                tclargs=[str(run), str(root / "tests/fixtures/ip/axis_register_slice/faulty_stream.vhd")],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            result = runner.run(description="Run stream checker fixture:", source=root / "tcl/run_xsim_batch.tcl",
                tclargs=[str(run / "proj/framework_negative.xpr"), str(testbench), "tb_stream_selfcheck",
                         "AXIS_SELF_CHECK_STATUS: PASS", "AXIS_SELF_CHECK_STATUS: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
        self.assertEqual(result.returncode, 0 if mode == 0 else 1, result.output[-3000:])
        self.assertIn(marker, result.output)
        if mode == 0:
            self.assertEqual(paths["actual_output"].read_bytes(), paths["expected_output"].read_bytes())
        if mode == 1:
            self.assertIn("XXXXXXXX", paths["protocol_events"].read_text())

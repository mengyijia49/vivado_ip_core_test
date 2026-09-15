from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout
from vivado_ip_test.plugins.reduced_logic.plugin import ReducedLogicPlugin
from vivado_ip_test.plugins.common.testbench import render_testbench
from vivado_ip_test.strategies import create_default_strategy_registry


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class CycleFailureDetectionTests(unittest.TestCase):
    def test_scalar_unknown_is_rejected_and_preserved(self):
        root = Path(__file__).resolve().parents[2]
        layout = RepositoryLayout(root)
        run = root / "runs/framework/failure_detection" / layout.run_id / "reduced_logic"
        logs = root / "runs/logs/framework/failure_detection" / layout.run_id / "reduced_logic"
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        plugin = ReducedLogicPlugin(layout, create_default_strategy_registry())
        spec = plugin.describe({"width": 1, "operation": "xor"})
        paths = {key: run / f"{key}.txt" for key in ("input_vectors", "expected_output", "actual_output")}
        paths["input_vectors"].write_text("0\n")
        paths["expected_output"].write_text("0\n")
        testbench = run / "tb_cycle_selfcheck.vhd"
        testbench.write_text(render_testbench(spec, paths, 1))
        vivado = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = vivado.run(description="创建逐周期故障注入工程：",
                source=root / "tests/fixtures/create_testbench_project.tcl",
                tclargs=[str(run), str(root / "tests/fixtures/ip/reduced_logic/unknown_output.vhd")],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            simulated = vivado.run(description="检查逐周期后端能否捕获未知值：",
                source=root / "tcl/run_xsim_batch.tcl",
                tclargs=[str(run / "proj/framework_negative.xpr"), str(testbench), "tb_cycle_selfcheck",
                         "CYCLE_SELF_CHECK_STATUS: PASS", "CYCLE_SELF_CHECK_STATUS: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
        self.assertEqual(simulated.returncode, 1, simulated.output[-2000:])
        self.assertIn("expected=0 actual=X", simulated.output)
        self.assertEqual(paths["actual_output"].read_text().strip(), "X")

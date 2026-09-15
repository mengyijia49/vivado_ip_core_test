from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout, output_files_match
from vivado_ip_test.plugins.common.testbench import packed, render_testbench
from vivado_ip_test.plugins.multiply_adder.plugin import MultiplyAdderPlugin
from vivado_ip_test.strategies import create_default_strategy_registry


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class MultiplyAdderFailureDetectionTests(unittest.TestCase):
    def check_fixture(self, scenario, second, should_pass, wrong_port=None):
        root = Path(__file__).resolve().parents[2]
        layout = RepositoryLayout(root)
        run = root / "runs/framework/failure_detection" / layout.run_id / "multiply_adder" / scenario
        logs = root / "runs/logs/framework/failure_detection" / layout.run_id / "multiply_adder" / scenario
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        plugin = MultiplyAdderPlugin(layout, create_default_strategy_registry())
        spec = plugin.describe({"a_width": 2, "b_width": 2, "c_width": 2,
            "a_type": "Unsigned", "b_type": "Unsigned", "c_type": "Unsigned", "output_high": 2,
            "output_low": 0, "pipelined": False, "use_pcin": False, "ce_overrides_reset": False},
            {"ab_latency": 0, "c_latency": 0, "implementation": 0})
        rows = [spec.frame({"A": 1, "B": 2, "C": 1}), spec.frame(second)]
        model = spec.model_factory()
        paths = {key: run / f"{key}.txt" for key in ("input_vectors", "expected_output", "actual_output")}
        paths["input_vectors"].write_text("".join(packed(row, spec.inputs) + "\n" for row in rows))
        expected = [packed(model.step(row), spec.outputs) for row in rows]
        paths["expected_output"].write_text("\n".join(expected) + "\n")
        tb = run / "tb_cycle_selfcheck.vhd"
        tb.write_text(render_testbench(spec, paths, len(rows)))
        vivado = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = vivado.run(description="创建乘加检查器测试工程：",
                source=root / "tests/fixtures/create_testbench_project.tcl",
                tclargs=[str(run), str(root / "tests/fixtures/ip/multiply_adder/faulty_outputs.vhd")],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            simulated = vivado.run(description="检查乘加双输出：", source=root / "tcl/run_xsim_batch.tcl",
                tclargs=[str(run / "proj/framework_negative.xpr"), str(tb), "tb_cycle_selfcheck",
                         "CYCLE_SELF_CHECK_STATUS: PASS", "CYCLE_SELF_CHECK_STATUS: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
        self.assertEqual(simulated.returncode, 0 if should_pass else 1, simulated.output[-3000:])
        self.assertEqual(output_files_match(paths["expected_output"], paths["actual_output"]), should_pass)
        actual = paths["actual_output"].read_text().splitlines()
        self.assertEqual(actual[0], expected[0])
        self.assertEqual(len(actual), 2)
        if not should_pass:
            self.assertIn("FAIL cycle=1", simulated.output)
            preserved = slice(0, 3) if wrong_port == "PCOUT" else slice(3, None)
            self.assertEqual(actual[1][preserved], expected[1][preserved])

    def test_correct_control(self):
        self.check_fixture("control", {"A": 2, "B": 3, "C": 1}, True)

    def test_cascade_only_corruption_is_detected(self):
        self.check_fixture("cascade_error", {"A": 1, "B": 1, "C": 2, "SUBTRACT": 1}, False, "PCOUT")

    def test_reversed_subtraction_is_detected(self):
        self.check_fixture("subtraction_error", {"A": 1, "B": 2, "C": 3, "SUBTRACT": 1}, False, "P")

from contextlib import redirect_stdout
from dataclasses import replace
import io
import os
from pathlib import Path
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout, output_files_match
from vivado_ip_test.plugins.common.testbench import render_testbench
from vivado_ip_test.plugins.vector_logic.plugin import VectorLogicPlugin
from vivado_ip_test.strategies import create_default_strategy_registry


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class MaskedFailureDetectionTests(unittest.TestCase):
    def check_fixture(self, name, expected, masks, returncode):
        root = Path(__file__).resolve().parents[2]
        layout = RepositoryLayout(root)
        run = root / "runs/framework/failure_detection" / layout.run_id / "vector_logic" / name
        logs = root / "runs/logs/framework/failure_detection" / layout.run_id / "vector_logic" / name
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        plugin = VectorLogicPlugin(layout, create_default_strategy_registry())
        spec = replace(plugin.describe({"width": 2, "operation": "xor"}), masked_outputs=True)
        paths = {key: run / f"{key}.txt" for key in
                 ("input_vectors", "expected_output", "expected_mask", "actual_output")}
        paths["input_vectors"].write_text("0000\n0100\n")
        paths["expected_output"].write_text(expected)
        paths["expected_mask"].write_text(masks)
        tb = run / "tb_cycle_selfcheck.vhd"
        tb.write_text(render_testbench(spec, paths, 2))
        vivado = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = vivado.run(description="创建有效位比较测试工程：",
                source=root / "tests/fixtures/create_testbench_project.tcl",
                tclargs=[str(run), str(root / "tests/fixtures/ip/vector_logic/masked_output.vhd")],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            simulated = vivado.run(description="检查有效位比较：", source=root / "tcl/run_xsim_batch.tcl",
                tclargs=[str(run / "proj/framework_negative.xpr"), str(tb), "tb_cycle_selfcheck",
                         "CYCLE_SELF_CHECK_STATUS: PASS", "CYCLE_SELF_CHECK_STATUS: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
        self.assertEqual(simulated.returncode, returncode, simulated.output[-3000:])
        self.assertEqual(paths["actual_output"].read_text(), "X0\nX1\n")
        self.assertEqual(output_files_match(paths["expected_output"], paths["actual_output"],
                         mask_path=paths["expected_mask"]), returncode == 0)
        if returncode:
            self.assertIn("FAIL cycle=1", simulated.output)

    def test_undefined_bit_is_preserved_but_not_compared(self):
        self.check_fixture("undefined_control", "00\n01\n", "01\n01\n", 0)

    def test_defined_bit_corruption_still_fails(self):
        self.check_fixture("defined_corruption", "00\n00\n", "01\n01\n", 1)

    def test_unknown_on_a_defined_bit_still_fails(self):
        self.check_fixture("defined_unknown", "00\n01\n", "01\n11\n", 1)

import os
from pathlib import Path
from string import Template
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner
from vivado_ip_test.infrastructure.run_identity import create_run_id


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class FailureDetectionTests(unittest.TestCase):
    def run_fixture(self, ip_type, fixture):
        root = Path(__file__).resolve().parents[2]
        run_id = create_run_id()
        vivado = VivadoBatchRunner(CommandRunner(), root / "runs/framework/work" / run_id)
        self.assertIsNotNone(vivado.executable)
        run_dir = root / "runs/framework/failure_detection" / run_id / ip_type
        log_dir = root / "runs/logs/framework/failure_detection" / run_id / ip_type
        run_dir.mkdir(parents=True)
        log_dir.mkdir(parents=True)
        input_path = run_dir / "input.txt"
        expected_path = run_dir / "expected.txt"
        actual_path = run_dir / "actual.txt"
        gaps_path = run_dir / "gaps.txt"
        input_path.write_text("01 01\n")
        expected_path.write_text("0001\n")
        gaps_path.write_text("0\n")
        top = f"tb_{ip_type}_selfcheck"
        template_path = root / f"src/vivado_ip_test/plugins/{ip_type}/templates/{top}.vhd.tpl"
        testbench_path = run_dir / f"{top}.vhd"
        testbench_path.write_text(Template(template_path.read_text()).substitute(
            dividend_width=2, divisor_width=2, dout_width=4,
            a_width=2, b_width=2, output_width=4, latency=1,
            vector_count=1, timeout_cycles=30,
            input_path=input_path, expected_path=expected_path, actual_path=actual_path,
            gaps_path=gaps_path,
        ))
        dut_path = root / "tests/fixtures/ip" / ip_type / fixture
        created = vivado.run(
            description="创建故障注入用测试工程：",
            source=root / "tests/fixtures/create_testbench_project.tcl",
            tclargs=[str(run_dir), str(dut_path)],
            journal_path=log_dir / "create.jou", log_path=log_dir / "create.log", timeout_sec=90,
        )
        self.assertEqual(created.returncode, 0, created.output[-2000:])
        marker = f"{ip_type.upper()}_SELF_CHECK_STATUS: "
        simulated = vivado.run(
            description="验证测试框架能捕获注入错误：",
            source=root / "tcl/run_xsim_batch.tcl",
            tclargs=[str(run_dir / "proj/framework_negative.xpr"), str(testbench_path), top, marker + "PASS", marker + "FAIL"],
            journal_path=log_dir / "simulate.jou", log_path=log_dir / "simulate.log", timeout_sec=90,
        )
        self.assertEqual(simulated.returncode, 1, simulated.output[-3000:])
        self.assertIn("XSIM_STAGE_STATUS: FAIL", simulated.output)
        return simulated, actual_path

    def test_selfcheck_preserves_first_bad_value_and_unknown_bits(self):
        for ip_type in ("divider", "multiplier"):
            with self.subTest(ip_type=ip_type):
                simulated, actual_path = self.run_fixture(ip_type, "unknown_output.vhd")
                self.assertIn("mismatch at output0 expected=0001 actual=XXXX", simulated.output)
                self.assertEqual(actual_path.read_text().strip(), "XXXX")

    def test_selfcheck_detects_spurious_divider_valid(self):
        simulated, _ = self.run_fixture("divider", "early_valid.vhd")
        self.assertIn("valid timing at cycle0", simulated.output)

from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout, output_files_match
from vivado_ip_test.plugins.common.testbench import normalize_expected, packed, render_testbench
from vivado_ip_test.plugins.complex_multiplier.plugin import ComplexMultiplierPlugin
from vivado_ip_test.plugins.complex_multiplier.vectors import pack_complex
from vivado_ip_test.strategies import create_default_strategy_registry


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class ComplexMultiplierFailureDetectionTests(unittest.TestCase):
    def check_fixture(self, scenario, second, should_pass):
        root = Path(__file__).resolve().parents[2]
        layout = RepositoryLayout(root)
        run = root / "runs/framework/failure_detection" / layout.run_id / "complex_multiplier" / scenario
        logs = root / "runs/logs/framework/failure_detection" / layout.run_id / "complex_multiplier" / scenario
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        plugin = ComplexMultiplierPlugin(layout, create_default_strategy_registry())
        case = load_test_cases(root / "configs/ip/complex_multiplier/regression.json")[0]
        spec = plugin.describe({**case.parameters, "a_width": 8, "b_width": 8, "output_width": 17, "latency": 0})
        first = {"s_axis_a_tdata": pack_complex(3, 4, 8), "s_axis_b_tdata": pack_complex(5, -2, 8),
                 "s_axis_a_tvalid": 1, "s_axis_b_tvalid": 1}
        rows = [spec.frame(first), spec.frame({**first, **second})]
        model = spec.model_factory()
        paths = {key: run / f"{key}.txt" for key in ("input_vectors", "expected_output", "actual_output", "expected_mask")}
        paths["input_vectors"].write_text("".join(packed(row, spec.inputs) + "\n" for row in rows))
        expected, masks = [], []
        for row in rows:
            values, mask, _ = normalize_expected(spec, model.step(row))
            expected.append(packed(values, spec.outputs))
            masks.append(packed(mask, spec.outputs))
        paths["expected_output"].write_text("\n".join(expected) + "\n")
        paths["expected_mask"].write_text("\n".join(masks) + "\n")
        tb = run / "tb_cycle_selfcheck.vhd"
        tb.write_text(render_testbench(spec, paths, len(rows)))
        vivado = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = vivado.run(description="创建复数乘法检查器测试工程：",
                source=root / "tests/fixtures/create_testbench_project.tcl",
                tclargs=[str(run), str(root / "tests/fixtures/ip/complex_multiplier/faulty_outputs.vhd")],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            simulated = vivado.run(description="检查复数乘法有效信号和扩展位：", source=root / "tcl/run_xsim_batch.tcl",
                tclargs=[str(run / "proj/framework_negative.xpr"), str(tb), "tb_cycle_selfcheck",
                         "CYCLE_SELF_CHECK_STATUS: PASS", "CYCLE_SELF_CHECK_STATUS: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
        self.assertEqual(simulated.returncode, 0 if should_pass else 1, simulated.output[-3000:])
        self.assertEqual(output_files_match(paths["expected_output"], paths["actual_output"],
                                           mask_path=paths["expected_mask"]), should_pass)
        actual = paths["actual_output"].read_text().splitlines()
        self.assertEqual(len(actual), 2)
        self.assertEqual(actual[0], expected[0])
        if not should_pass:
            self.assertIn("FAIL cycle=1", simulated.output)
        if scenario == "padding_error":
            self.assertEqual(actual[1][0], expected[1][0])
            self.assertEqual(actual[1][-17:], expected[1][-17:])
            self.assertNotEqual(actual[1][-24:-17], expected[1][-24:-17])
        if scenario == "valid_error":
            self.assertEqual(masks[1], "1" + "0" * 48)
            self.assertNotEqual(actual[1][0], expected[1][0])

    def test_correct_control(self):
        self.check_fixture("control", {}, True)

    def test_output_sign_extension_corruption_is_detected(self):
        self.check_fixture("padding_error", {"s_axis_a_tdata": pack_complex(-1, 0, 8),
            "s_axis_b_tdata": pack_complex(1, 0, 8)}, False)

    def test_unqualified_output_is_detected_even_when_data_is_masked(self):
        self.check_fixture("valid_error", {"s_axis_a_tvalid": 0}, False)

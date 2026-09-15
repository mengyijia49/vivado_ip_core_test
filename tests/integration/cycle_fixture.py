from contextlib import redirect_stdout
import io
from pathlib import Path

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout, output_files_match
from vivado_ip_test.plugins.common.testbench import render_testbench
from vivado_ip_test.strategies import create_default_strategy_registry


def run_cycle_fixture(test, plugin_type, parameters, rows, mode, name, *, malformed=False, expected_error=None,
                      masks=None, fixture_file="faulty_dut.vhd"):
    root = Path(__file__).resolve().parents[2]
    layout = RepositoryLayout(root)
    plugin = plugin_type(layout, create_default_strategy_registry())
    spec = plugin.describe(parameters)
    run = root / "runs/framework/failure_detection" / layout.run_id / plugin.ip_type / name
    logs = root / "runs/logs/framework/failure_detection" / layout.run_id / plugin.ip_type / name
    run.mkdir(parents=True)
    logs.mkdir(parents=True)
    paths = {key: run / f"{key}.txt" for key in ("input_vectors", "expected_output", "actual_output")}
    paths["input_vectors"].write_text("".join(stimulus + "\n" for stimulus, _ in rows))
    paths["expected_output"].write_text("".join(expected + "\n" for _, expected in rows))
    if masks is not None:
        test.assertEqual(len(masks), len(rows))
        paths["expected_mask"] = run / "expected_mask.txt"
        paths["expected_mask"].write_text("".join(mask + "\n" for mask in masks))
    tb = run / "tb_cycle_selfcheck.vhd"
    tb.write_text(render_testbench(spec, paths, len(rows)).replace(
        "port map (", f"generic map (fault_mode => {mode})\n    port map (", 1))
    runner = VivadoBatchRunner(CommandRunner(), run / "work")
    with redirect_stdout(io.StringIO()):
        result = runner.run(description="Create cycle checker fixture:",
            source=root / "tests/fixtures/create_testbench_project.tcl",
            tclargs=[str(run), str(root / "tests/fixtures/ip" / plugin.ip_type / fixture_file)],
            log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
        test.assertEqual(result.returncode, 0, result.output[-3000:])
        result = runner.run(description="Run cycle checker fixture:", source=root / "tcl/run_xsim_batch.tcl",
            tclargs=[str(run / "proj/framework_negative.xpr"), str(tb), "tb_cycle_selfcheck",
                     "CYCLE_SELF_CHECK_STATUS: PASS", "CYCLE_SELF_CHECK_STATUS: FAIL"],
            log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
    failed = mode != 0 or malformed or expected_error is not None
    test.assertEqual(result.returncode, int(failed), result.output[-3000:])
    test.assertIn("CYCLE_SELF_CHECK_STATUS: " + ("FAIL" if failed else "PASS"), result.output)
    if expected_error is not None:
        test.assertIn(expected_error, result.output)
    elif malformed:
        test.assertIn("unexpected data for inputless DUT", result.output)
    elif failed:
        test.assertRegex(result.output, r"cycle=\d+ expected=[01]+ actual=[01X]+")
        test.assertTrue(paths["actual_output"].read_text())
    else:
        test.assertTrue(output_files_match(paths["expected_output"], paths["actual_output"],
                                          mask_path=paths.get("expected_mask")))
    return result, paths

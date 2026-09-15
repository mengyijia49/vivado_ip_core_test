from contextlib import redirect_stdout
import io
from pathlib import Path

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout, output_files_match
from vivado_ip_test.plugins.catalog import create_plugin_registry
from vivado_ip_test.plugins.common.testbench import packed, render_testbench
from vivado_ip_test.strategies import create_default_strategy_registry


def check_fixture(test, ip_type, scenario, second, should_pass):
    root = Path(__file__).resolve().parents[3]
    layout = RepositoryLayout(root)
    run = root / "runs/framework/failure_detection" / layout.run_id / ip_type / scenario
    logs = root / "runs/logs/framework/failure_detection" / layout.run_id / ip_type / scenario
    run.mkdir(parents=True)
    logs.mkdir(parents=True)
    registry = create_plugin_registry(layout, create_default_strategy_registry())
    plugin = registry.resolve(ip_type)
    case = load_test_cases(root / f"configs/ip/{ip_type}/regression.json")[0]
    parameters = {**case.parameters, "width": 8}
    if ip_type == "tmr_voter":
        parameters["comparator"] = True
    spec = plugin.describe(parameters)
    first = {"Discrete1": 3, "Discrete2": 5, "Discrete3": 6}
    if ip_type == "tmr_comparator":
        first["Discrete"] = 7
    rows = [spec.frame(first), spec.frame(second)]
    model = spec.model_factory()
    paths = {key: run / f"{key}.txt" for key in ("input_vectors", "expected_output", "actual_output")}
    paths["input_vectors"].write_text("".join(packed(row, spec.inputs) + "\n" for row in rows))
    expected = [packed(model.step(row), spec.outputs) for row in rows]
    paths["expected_output"].write_text("\n".join(expected) + "\n")
    tb = run / "tb_cycle_selfcheck.vhd"
    tb.write_text(render_testbench(spec, paths, len(rows)))
    vivado = VivadoBatchRunner(CommandRunner(), run / "work")
    with redirect_stdout(io.StringIO()):
        created = vivado.run(description="创建冗余检查器测试工程：",
            source=root / "tests/fixtures/create_testbench_project.tcl",
            tclargs=[str(run), str(root / f"tests/fixtures/ip/{ip_type}/faulty_outputs.vhd")],
            log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
        test.assertEqual(created.returncode, 0, created.output[-2000:])
        simulated = vivado.run(description="检查错误投票与告警是否被捕获：",
            source=root / "tcl/run_xsim_batch.tcl",
            tclargs=[str(run / "proj/framework_negative.xpr"), str(tb), "tb_cycle_selfcheck",
                     "CYCLE_SELF_CHECK_STATUS: PASS", "CYCLE_SELF_CHECK_STATUS: FAIL"],
            log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
    test.assertEqual(simulated.returncode, 0 if should_pass else 1, simulated.output[-3000:])
    test.assertEqual(output_files_match(paths["expected_output"], paths["actual_output"]), should_pass)
    actual = paths["actual_output"].read_text().splitlines()
    test.assertEqual(len(actual), 2)
    test.assertEqual(actual[0], expected[0])
    if not should_pass:
        test.assertIn("FAIL cycle=1", simulated.output)
        if scenario == "vote_error":
            test.assertEqual(actual[1][-4:], expected[1][-4:])
        if scenario == "compare_error":
            test.assertEqual(actual[1][:-4], expected[1][:-4])

from contextlib import redirect_stdout
import io
import json
from pathlib import Path

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout, output_files_match, sha256_file
from vivado_ip_test.plugins.common.metadata import setting_text
from vivado_ip_test.plugins.common.testbench import render_testbench
from vivado_ip_test.plugins.fifo_generator.plugin import FifoGeneratorPlugin
from vivado_ip_test.strategies import create_default_strategy_registry


def run_literal_trace(test, parameters, rows, masks, name):
    root = Path(__file__).resolve().parents[4]
    layout = RepositoryLayout(root)
    plugin = FifoGeneratorPlugin(layout, create_default_strategy_registry())
    spec = plugin.describe(parameters)
    run = root / "runs/framework/protocol_probe" / layout.run_id / "fifo_generator" / name
    logs = root / "runs/logs/framework/protocol_probe" / layout.run_id / "fifo_generator" / name
    run.mkdir(parents=True)
    logs.mkdir(parents=True)
    paths = {key: run / f"{key}.txt" for key in
             ("input_vectors", "expected_output", "expected_mask", "actual_output")}
    paths["input_vectors"].write_text("".join(row[0] + "\n" for row in rows))
    paths["expected_output"].write_text("".join(row[1] + "\n" for row in rows))
    paths["expected_mask"].write_text("".join(mask + "\n" for mask in masks))
    tb = run / "tb_cycle_selfcheck.vhd"
    tb.write_text(render_testbench(spec, paths, len(rows)))
    (run / "parameters.json").write_text(json.dumps({"parameters": parameters,
        "testbench_sha256": sha256_file(tb), "input_sha256": sha256_file(paths["input_vectors"]),
        "expected_sha256": sha256_file(paths["expected_output"]),
        "mask_sha256": sha256_file(paths["expected_mask"])}, indent=2) + "\n")
    runner = VivadoBatchRunner(CommandRunner(), run / "work")
    with redirect_stdout(io.StringIO()):
        created = runner.run(description="Create FIFO literal-trace probe:",
            source=root / "tcl/ip/fifo_generator/create_ip.tcl",
            tclargs=[str(run), *(part for key, value in spec.settings.items()
                                for part in (f"CONFIG.{key}", setting_text(value)))],
            log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
        test.assertEqual(created.returncode, 0, created.output[-3000:])
        simulated = runner.run(description="Check FIFO literal trace:", source=root / "tcl/run_xsim_batch.tcl",
            tclargs=[str(run / "proj/ip_test.xpr"), str(tb), "tb_cycle_selfcheck",
                     "CYCLE_SELF_CHECK_STATUS: PASS", "CYCLE_SELF_CHECK_STATUS: FAIL"],
            log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
    test.assertEqual(simulated.returncode, 0, simulated.output[-3000:])
    test.assertTrue(output_files_match(paths["expected_output"], paths["actual_output"],
                                      mask_path=paths["expected_mask"]))

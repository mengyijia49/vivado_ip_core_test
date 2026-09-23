from contextlib import redirect_stdout
import io
import json
from pathlib import Path

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner


def run_protocol_probe(test, run_id, ip_type, case, settings, render, top, marker):
    root = Path(__file__).resolve().parents[3]
    run = root / "runs/framework/protocol_review/2026.1" / run_id / ip_type / case
    logs = root / "runs/logs/framework/protocol_review/2026.1" / run_id / ip_type / case
    run.mkdir(parents=True)
    tb = run / f"{top}.vhd"
    tb.write_text(render(run))
    (run / "settings.json").write_text(json.dumps(settings, indent=2) + "\n")
    runner = VivadoBatchRunner(CommandRunner(), run / "work")
    with redirect_stdout(io.StringIO()):
        created = runner.run(description="Create protocol review probe",
            source=root / f"tcl/ip/{ip_type}/create_ip.tcl",
            tclargs=[str(run), *[item for k, v in settings.items()
                                for item in (f"CONFIG.{k}", str(v))]],
            log_path=logs / "create.log", journal_path=logs / "create.jou")
        test.assertIsNotNone(created)
        test.assertEqual(created.returncode, 0, created.output[-3000:])
        simulated = runner.run(description="Run protocol review probe",
            source=root / "tcl/run_xsim_batch.tcl",
            tclargs=[str(run / "proj/ip_test.xpr"), str(tb), top,
                     f"{marker}: PASS", f"{marker}: FAIL"],
            log_path=logs / "simulate.log", journal_path=logs / "simulate.jou")
    test.assertIsNotNone(simulated)
    test.assertEqual(simulated.returncode, 0, simulated.output[-3000:])
    print(f"{ip_type}/{case}: {run}", flush=True)
    return run, simulated.output

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import shutil
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout, sha256_file


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class TimerProbeTests(unittest.TestCase):
    def test_independent_timer_windows(self):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        run = root / "runs/framework/timer_probe" / layout.run_id / "axi_timer"
        logs = root / "runs/logs/framework/timer_probe" / layout.run_id / "axi_timer"
        report = root / "reports/framework/timer_probe" / layout.run_id
        for path in (run, logs, report):
            path.mkdir(parents=True)
        fixture = root / "tests/fixtures/ip/axi_timer/tb_timer_probe.vhd"
        snapshot = run / fixture.name
        shutil.copy2(fixture, snapshot)
        parameters = {"CONFIG.COUNT_WIDTH": "8", "CONFIG.enable_timer2": "1", "CONFIG.mode_64bit": "0"}
        runner = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = runner.run(description="Create independent Timer probe:",
                source=root / "tcl/diagnostics/inspect_ip.tcl",
                tclargs=[str(run), "axi_timer", *[item for pair in parameters.items() for item in pair]],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=120)
            self.assertIsNotNone(created)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            result = runner.run(description="Observe Timer with fixed clock windows:",
                source=root / "tcl/run_xsim_batch.tcl", tclargs=[str(run / "proj/ip_probe.xpr"), str(snapshot),
                    "tb_timer_probe", "TIMER_PROBE: COMPLETE", "TIMER_PROBE: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=120)
        observations = {name: {"read": int(data, 16), "irq": int(irq), "pulse0": int(p0), "pulse1": int(p1)}
            for name, data, irq, p0, p1 in re.findall(
                r"TIMER_OBSERVATION (\w+)=([0-9A-F]+) irq='([01])' pulse0=(\d+) pulse1=(\d+)", result.output)}
        summary = {"run_id": layout.run_id, "classification": "TIMING_OBSERVATION",
            "completion_is_not_a_bug_confirmation": True, "parameters": parameters,
            "fixture_sha256": sha256_file(snapshot), "observations": observations,
            "pulses": [[int(channel), int(cycle)] for channel, cycle in
                       re.findall(r"TIMER_PULSE channel=(\d+) cycle=(\d+)", result.output)],
            "returncode": result.returncode}
        (report / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(f"Timer probe: {layout.run_id}")
        self.assertEqual(result.returncode, 0, result.output[-3000:])
        self.assertIn("enall_clear1", observations)

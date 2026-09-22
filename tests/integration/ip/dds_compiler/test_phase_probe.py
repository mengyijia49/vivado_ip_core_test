from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout, sha256_file


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1",
                     "需显式启用真实 Vivado 集成测试")
class DdsPhaseProbeTests(unittest.TestCase):
    def test_fixed_phase_reset_and_backpressure(self):
        root = Path(__file__).resolve().parents[4]
        run_id = RepositoryLayout(root).run_id
        run = root / "runs/framework/dds_phase_probe" / run_id / "dds_compiler"
        logs = root / "runs/logs/framework/dds_phase_probe" / run_id / "dds_compiler"
        reports = root / "reports/framework/dds_phase_probe" / run_id
        for path in (run, logs, reports):
            path.mkdir(parents=True)
        fixture = root / "tests/fixtures/ip/dds_compiler/phase_probe.vhd"
        settings = {"PartsPresent": "Phase_Generator_only", "Parameter_Entry": "Hardware_Parameters",
            "Phase_Width": 8, "Phase_Increment": "Fixed", "PINC1": "00010001",
            "Phase_offset": "None", "Has_Phase_Out": True, "Has_TREADY": True,
            "Has_ARESETn": True, "Resync": False,
            "Latency_Configuration": "Configurable", "Latency": 4}
        args = [str(run), "dds_compiler", *(item for key, value in settings.items()
                for item in ("CONFIG." + key, str(value).lower() if isinstance(value, bool) else str(value)))]
        runner = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = runner.run(description="Create independent DDS phase probe:",
                source=root / "tcl/diagnostics/inspect_ip.tcl", tclargs=args,
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=120)
            self.assertEqual(created.returncode, 0, created.output[-3000:])
            simulated = runner.run(description="Run independent DDS phase probe:",
                source=root / "tcl/run_xsim_batch.tcl",
                tclargs=[str(run / "proj/ip_probe.xpr"), str(fixture), "tb_dds_phase_probe",
                         "DDS_PHASE_PROBE_STATUS: PASS", "DDS_PHASE_PROBE_STATUS: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=120)
        rows = {int(c): {"resetn": int(r), "ready": int(rd), "valid": int(v), "data": int(d)}
                for c, r, rd, v, d in re.findall(
                    r"DDS_PHASE_SAMPLE cycle=(\d+) resetn='([01])' ready='([01])' valid='([01])' data=(\d+)",
                    simulated.output)}
        summary = {"run_id": run_id, "settings": settings, "returncode": simulated.returncode,
                   "observations": rows, "fixture_sha256": sha256_file(fixture)}
        (reports / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        self.assertEqual(simulated.returncode, 0, simulated.output[-3000:])
        self.assertEqual(rows[8]["data"], 17)
        self.assertEqual([rows[i]["data"] for i in range(11, 15)], [51] * 4)
        self.assertEqual(rows[20]["valid"], 0)

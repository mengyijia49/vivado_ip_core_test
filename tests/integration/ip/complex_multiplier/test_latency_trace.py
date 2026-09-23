from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import shutil
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, sha256_file
from vivado_ip_test.infrastructure.run_identity import create_run_id


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "Requires Vivado integration opt-in")
class LatencyTraceTests(unittest.TestCase):
    def test_latency_controls_and_long_pipeline(self):
        root = Path(__file__).resolve().parents[4]
        run_id = create_run_id()
        base = root / "runs/framework/latency_trace/2026.1" / run_id / "complex_multiplier"
        logs = root / "runs/logs/framework/latency_trace/2026.1" / run_id / "complex_multiplier"
        report = root / "reports/history/2026.1" / run_id / "complex_multiplier"
        report.mkdir(parents=True)
        fixture = root / "tests/fixtures/ip/complex_multiplier/tb_latency_trace.vhd"
        summaries = []
        for requested in (-1, 4, 16, 54, 55):
            case = "auto" if requested == -1 else f"latency_{requested}"
            run = base / case
            run.mkdir(parents=True)
            tb = run / fixture.name
            shutil.copyfile(fixture, tb)
            runner = VivadoBatchRunner(CommandRunner(), run / "work")
            settings = {"DataType": "Integer", "HasAccumulator": "false",
                "APortWidth": "8", "BPortWidth": "8", "OutputWidth": "16",
                "MultType": "Use_Mults", "OptimizeGoal": "Performance",
                "FlowControl": "NonBlocking", "RoundMode": "Truncate",
                "LatencyConfig": "Automatic" if requested == -1 else "Manual",
                "ACLKEN": "false", "ARESETN": "false", "OutTLASTBehv": "Null"}
            for channel in ("A", "B", "CTRL"):
                settings[f"Has{channel}TLAST"] = "false"
                settings[f"Has{channel}TUSER"] = "false"
            if requested != -1:
                settings["MinimumLatency"] = str(requested)
            with redirect_stdout(io.StringIO()):
                created = runner.run(description="Create latency trace probe",
                    source=root / "tcl/ip/complex_multiplier/create_ip.tcl",
                    tclargs=[str(run), *[item for k, v in settings.items() for item in (f"CONFIG.{k}", v)]],
                    log_path=logs / case / "create.log", journal_path=logs / case / "create.jou")
                self.assertIsNotNone(created)
                self.assertEqual(created.returncode, 0, created.output[-3000:])
                xci = run / "proj/ip_test.srcs/sources_1/ip/dut_0/dut_0.xci"
                parameters = json.loads(xci.read_text())["ip_inst"]["parameters"]
                latency = int(parameters["model_parameters"]["C_LATENCY"][0]["value"])
                wrapper = run / "proj/ip_test.gen/sources_1/ip/dut_0/sim/dut_0.vhd"
                self.assertRegex(wrapper.read_text(), rf"C_LATENCY\s*=>\s*{latency}\s*,")
                simulated = runner.run(description="Observe complete latency trace",
                    source=root / "tcl/run_xsim_batch.tcl",
                    tclargs=[str(run / "proj/ip_test.xpr"), str(tb), "tb_latency_trace", "CMPY_TRACE: COMPLETE"],
                    log_path=logs / case / "simulate.log", journal_path=logs / case / "simulate.jou")
            self.assertIsNotNone(simulated)
            rows = [{"cycle": int(c), "input": a, "vin": vi, "before": b, "output": d, "vout": vo}
                    for c, a, vi, b, d, vo in re.findall(
                        r"CMPY_TRACE cycle=(\d+) input=(\w+) vin='(.)' before=(\w+) output=(\w+) vout='(.)'",
                        simulated.output)]
            mismatches = []
            for row in rows:
                source_cycle = row["cycle"] - latency + 1
                if source_cycle < 0:
                    continue
                source = rows[source_cycle]
                expected = f"{int(source['input'], 16) // 2:08X}"
                if row["vout"] != source["vin"] or source["vin"] == "1" and row["output"] != expected:
                    mismatches.append({"cycle": row["cycle"], "expected_valid": source["vin"],
                        "actual_valid": row["vout"], "expected_output": expected, "actual_output": row["output"]})
            summary = {"case": case, "requested_latency": requested, "generated_latency": latency,
                "classification": "OBSERVATION_NOT_VENDOR_CONFIRMED", "rows": rows, "mismatches": mismatches,
                "fixture_sha256": sha256_file(fixture), "xci_sha256": sha256_file(xci),
                "wrapper_sha256": sha256_file(wrapper), "settings": settings,
                "parameters": parameters, "run_dir": str(run), "log_dir": str(logs / case),
                "returncode": simulated.returncode}
            (report / f"{case}.json").write_text(json.dumps(summary, indent=2) + "\n")
            summaries.append({k: summary[k] for k in ("case", "requested_latency", "generated_latency", "returncode")})
            summaries[-1]["mismatch_count"] = len(mismatches)
            (report / "summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
            print(f"{case}: generated={latency}, rows={len(rows)}, mismatches={len(mismatches)}; {report}", flush=True)
            self.assertEqual(simulated.returncode, 0, simulated.output[-3000:])
            self.assertEqual([row["cycle"] for row in rows], list(range(240)))
            if requested in (-1, 4):
                self.assertEqual(mismatches, [])

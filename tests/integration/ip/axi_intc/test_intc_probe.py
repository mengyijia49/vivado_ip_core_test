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
class IntcProbeTests(unittest.TestCase):
    def test_independent_mixed_interrupts(self):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        run = root / "runs/framework/intc_probe" / layout.run_id / "axi_intc"
        logs = root / "runs/logs/framework/intc_probe" / layout.run_id / "axi_intc"
        report = root / "reports/framework/intc_probe" / layout.run_id
        for path in (run, logs, report):
            path.mkdir(parents=True)
        fixture = root / "tests/fixtures/ip/axi_intc/tb_intc_probe.vhd"
        snapshot = run / fixture.name
        shutil.copy2(fixture, snapshot)
        parameters = {"C_NUM_INTR_INPUTS": "4", "C_NUM_SW_INTR": "2", "C_HAS_ILR": "1",
            "C_KIND_OF_INTR": "0x00000005", "C_KIND_OF_EDGE": "0x00000001",
            "C_KIND_OF_LVL": "0x00000002", "C_ASYNC_INTR": "0x00000000"}
        runner = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = runner.run(description="Create independent INTC probe:",
                source=root / "tcl/diagnostics/inspect_ip.tcl", tclargs=[str(run), "axi_intc",
                    *[v for k, value in parameters.items() for v in ("CONFIG."+k, value)]],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=120)
            self.assertIsNotNone(created)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            result = runner.run(description="Observe mixed hardware and software interrupts:",
                source=root / "tcl/run_xsim_batch.tcl", tclargs=[str(run / "proj/ip_probe.xpr"), str(snapshot),
                    "tb_intc_probe", "INTC_PROBE: COMPLETE", "INTC_PROBE: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=120)
        observations = {name: {"read": int(data, 16), "irq": int(irq)} for name, data, irq in
            re.findall(r"INTC_OBSERVATION (\w+)=([0-9A-F]+) irq='([01])'", result.output)}
        summary = {"run_id": layout.run_id, "classification": "REGISTER_OBSERVATION",
            "completion_is_not_a_bug_confirmation": True, "parameters": parameters,
            "fixture_sha256": sha256_file(snapshot), "observations": observations,
            "writes": [{"address": int(a), "strobe": int(s), "data": int(d, 16), "response": int(r, 16)}
                for a, s, d, r in re.findall(r"INTC_WRITE address=(\d+) strobe=(\d+) data=([0-9A-F]+) response=([0-9A-F]+)", result.output)],
            "returncode": result.returncode}
        (report / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(f"INTC probe: {layout.run_id}")
        self.assertEqual(result.returncode, 0, result.output[-3000:])
        self.assertIn("strobe_15", observations)

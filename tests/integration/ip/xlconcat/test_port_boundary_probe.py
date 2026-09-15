from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
from string import Template
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout, sha256_file


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class ConcatPortBoundaryProbeTests(unittest.TestCase):
    def test_legacy_127_control(self):
        self.run_probe(127, False, require_match=True)

    def test_legacy_128_observation(self):
        self.run_probe(128, False, require_match=False)

    def test_inline_128_control(self):
        self.run_probe(128, True, require_match=True)

    def test_legacy_128_fresh_source_observation(self):
        self.run_probe(128, False, require_match=False, fresh_source=True)

    def test_legacy_127_wide_without_vector_textio(self):
        self.run_probe(127, False, require_match=True, width=4096)

    def run_probe(self, count, inline, *, require_match, fresh_source=False, width=1):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        ip_type = "ilconcat" if inline else "xlconcat"
        run = root / "runs/framework/port_boundary_probe" / layout.run_id / ip_type / f"n{count}"
        logs = root / "runs/logs/framework/port_boundary_probe" / layout.run_id / ip_type / f"n{count}"
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        fixture = root / "tests/fixtures/ip/xlconcat/tb_port_boundary.vhd.tpl"
        tb = run / "tb_port_boundary.vhd"
        tb.write_text(Template(fixture.read_text()).substitute(last=count*width-1,
            mappings=",\n".join(f"      In{i} => stimulus({(i+1)*width-1} downto {i*width})" for i in range(count))))
        runner = VivadoBatchRunner(CommandRunner(), run / "work")
        parameters = ["CONFIG.NUM_PORTS", str(count)]
        if width != 1:
            parameters.extend(item for i in range(count) for item in (f"CONFIG.IN{i}_WIDTH", str(width)))
        with redirect_stdout(io.StringIO()):
            created = runner.run(description="Create independent concat port-count probe:",
                source=root / ("tcl/diagnostics/inspect_inline_hdl.tcl" if inline else "tcl/ip/xlconcat/create_ip.tcl"),
                tclargs=[str(run), *([ip_type] if inline else []), *parameters],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-3000:])
            project = run / "proj" / ("inline_probe.xpr" if inline else "ip_test.xpr")
            model_paths = []
            if fresh_source:
                generated = run / "proj/ip_test.gen/sources_1/bd/dut_0"
                model_paths = list(generated.glob("ipshared/*/hdl/xlconcat_v2_1_vl_rfs.v"))
                self.assertEqual(len(model_paths), 1)
                copied = runner.run(description="Compile supplied source model without precompiled IP library:",
                    source=root / "tests/fixtures/ip/xlconcat/create_source_probe.tcl",
                    tclargs=[str(run / "source_project"), str(model_paths[0]),
                             str(generated / "ip/dut_0_core_0/sim/dut_0_core_0.v"),
                             str(generated / "sim/dut_0.v")],
                    log_path=logs / "create_source.log", journal_path=logs / "create_source.jou", timeout_sec=90)
                self.assertEqual(copied.returncode, 0, copied.output[-3000:])
                project = run / "source_project/source_probe.xpr"
            simulated = runner.run(description="Observe concat without common generator or Python oracle:",
                source=root / "tcl/run_xsim_batch.tcl",
                tclargs=[str(project), str(tb), "tb_port_boundary",
                         "CONCAT_PORT_PROBE: COMPLETE", "CONCAT_PORT_PROBE: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
        rows = [{"name": name, "expected": expected, "actual": actual} for name, expected, actual in
                re.findall(r"CONCAT_PORT_OBSERVATION (\w+) expected=([01]+) actual=([01UXZWLH-]+)", simulated.output)]
        (run / "observations.json").write_text(json.dumps({"classification": "UNTRIAGED",
            "completion_is_not_a_bug_confirmation": True, "port_count": count, "port_width": width, "ip_type": ip_type,
            "fresh_source": fresh_source, "model_sha256": {str(p): sha256_file(p) for p in model_paths},
            "fixture_sha256": sha256_file(fixture), "rendered_testbench_sha256": sha256_file(tb),
            "observations": rows, "returncode": simulated.returncode}, indent=2) + "\n")
        self.assertEqual(simulated.returncode, 0, simulated.output[-3000:])
        self.assertEqual([row["name"] for row in rows], ["zero", "ones", "ones_late", "high", "low", "alternating"])
        self.assertTrue(all(len(row["actual"]) == count*width for row in rows))
        if require_match:
            self.assertTrue(all(row["actual"] == row["expected"] for row in rows), rows)

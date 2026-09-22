from contextlib import redirect_stdout
import io
import json
import inspect
from pathlib import Path
import re
import shutil

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout, sha256_file


def run_isolated_probe(test, *, name, marker, parameters, observation_count, fresh_source):
    root = Path(__file__).resolve().parents[4]
    layout = RepositoryLayout(root)
    run = root / f"runs/framework/{name}_probe" / layout.run_id / "axi_intc"
    logs = root / f"runs/logs/framework/{name}_probe" / layout.run_id / "axi_intc"
    report = root / f"reports/framework/{name}_probe" / layout.run_id
    for path in (run, logs, report):
        path.mkdir(parents=True)
    fixture = run / f"tb_{name}_probe.vhd"
    shutil.copy2(root / "tests/fixtures/ip/axi_intc" / fixture.name, fixture)
    scripts = {}
    for relative in ("tcl/diagnostics/inspect_ip.tcl", "tcl/run_xsim_batch.tcl",
                     "tests/fixtures/ip/axi_intc/create_source_probe.tcl"):
        target = run / "scripts" / Path(relative).name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(root / relative, target)
        scripts[target.name] = target
    for source in (Path(__file__), Path(inspect.getfile(type(test)))):
        target = run / "scripts" / source.name
        shutil.copy2(source, target)
        scripts[target.name] = target
    runner = VivadoBatchRunner(CommandRunner(), run / "work")
    with redirect_stdout(io.StringIO()):
        created = runner.run(description=f"Create isolated {name} probe:",
            source=scripts["inspect_ip.tcl"], tclargs=[str(run), "axi_intc",
                *[v for k, value in parameters.items() for v in ("CONFIG."+k, value)]],
            log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=120)
        test.assertIsNotNone(created)
        test.assertEqual(created.returncode, 0, created.output[-2000:])
        project = run / "proj/ip_probe.xpr"
        generated = run / "proj/ip_probe.gen/sources_1/ip/probe_0"
        model_files = list(generated.glob("hdl/axi_intc_v4_1*_rfs.vhd"))
        ipif_files = list(generated.glob("hdl/axi_lite_ipif_v3_*_rfs.vhd"))
        test.assertEqual(len(model_files), 1, model_files)
        test.assertEqual(len(ipif_files), 1, ipif_files)
        model = model_files[0]
        ipif = ipif_files[0]
        wrapper = generated / "sim/probe_0.vhd"
        if fresh_source:
            model_libraries = set(re.findall(r"(?i)library\s+(axi_intc_v4_1_\d+)\s*;", wrapper.read_text()))
            ipif_libraries = set(re.findall(r"(?i)library\s+(axi_lite_ipif_v3_\d+_\d+)\s*;", model.read_text()))
            test.assertEqual(len(model_libraries), 1)
            test.assertEqual(len(ipif_libraries), 1)
            copied = runner.run(description="Compile unmodified INTC and AXI-Lite source libraries:",
                source=scripts["create_source_probe.tcl"], tclargs=[str(run / "source_project"),
                    str(ipif), ipif_libraries.pop(), str(model), model_libraries.pop(), str(wrapper)],
                log_path=logs / "create_source.log", journal_path=logs / "create_source.jou", timeout_sec=120)
            test.assertEqual(copied.returncode, 0, copied.output[-2000:])
            project = run / "source_project/source_probe.xpr"
        result = runner.run(description=f"Check isolated {name} register semantics:",
            source=scripts["run_xsim_batch.tcl"], tclargs=[str(project), str(fixture),
                f"tb_{name}_probe", f"{marker}_PROBE: PASS", f"{marker}_PROBE: FAIL"],
            log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=120)
    observations = {name: {"expected": int(wanted), "actual": int(actual, 16),
        "irq": int(irq), "expected_irq": int(expected_irq)}
        for name, wanted, actual, irq, expected_irq in re.findall(
            rf"{marker}_OBSERVATION (\w+) expected=(\d+) actual=([0-9A-F]+) irq='([01])' expected_irq='([01])'",
            result.output)}
    xci = next(run.glob("proj/*.srcs/sources_1/ip/probe_0/*.xci"))
    data = json.loads(xci.read_text())["ip_inst"]
    summary = {"run_id": layout.run_id, "classification": "SPECIFICATION_CHECK_NOT_VENDOR_CONFIRMED",
        "parameters": parameters, "ip_revision": data["ip_revision"], "observations": observations,
        "fresh_source": fresh_source,
        "source_sha256": {str(p.relative_to(run)): sha256_file(p)
            for p in (model, ipif, wrapper, *scripts.values())},
        "difference_labels": re.findall(rf"{marker}_DIFFERENCE (\w+)", result.output),
        "fixture_sha256": sha256_file(fixture), "xci_sha256": sha256_file(xci),
        "returncode": result.returncode}
    (report / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"{name} probe: {layout.run_id}")
    test.assertEqual(result.returncode, 0, result.output[-2500:])
    test.assertEqual(len(observations), observation_count)

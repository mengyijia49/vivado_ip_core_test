from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout, sha256_file
from vivado_ip_test.plugins.common.metadata import setting_text
from vivado_ip_test.plugins.common.stream.testbench import render_testbench
from vivado_ip_test.plugins.common.testbench import packed
from vivado_ip_test.plugins.cordic.plugin import CordicPlugin
from vivado_ip_test.strategies import create_default_strategy_registry


PARAMETERS = {"function": "Square_Root", "input_width": 8, "output_width": 5,
              "data_format": "UnsignedInteger", "rounding": "Truncate", "architecture": "Parallel",
              "pipelining": "Maximum", "optimization": "Resources", "has_last": True, "user_width": 3}


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class CordicFailureDetectionTests(unittest.TestCase):
    def test_control_and_protocol_faults(self):
        names = ("control", "wrong_round", "unknown", "unstable", "drop", "extra", "last", "user", "padding")
        for mode, name in enumerate(names):
            with self.subTest(name=name):
                self.run_fixture(mode, name)

    def run_fixture(self, mode, name):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        spec = CordicPlugin(layout, create_default_strategy_registry()).describe(PARAMETERS)
        run = root / "runs/framework/failure_detection" / layout.run_id / "cordic" / name
        logs = root / "runs/logs/framework/failure_detection" / layout.run_id / "cordic" / name
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        paths = {key: run / f"{key}.txt" for key in ("input_vectors", "expected_output", "actual_output",
                 "gaps", "ready", "accepted_input", "protocol_events", "protocol_summary")}
        inputs = (0, 1, 2, 3, 4, 7, 8, 9, 15, 16, 224, 225, 255)
        roots = (0, 1, 1, 1, 2, 2, 2, 3, 3, 4, 14, 15, 15)
        for key, values, ports in (("input_vectors", inputs, spec.payload),
                                   ("expected_output", roots, spec.sink_payload)):
            paths[key].write_text("".join(packed({"tdata": value, "tlast": i % 2, "tuser": i % 8}, ports)
                                          + "\n" for i, value in enumerate(values)))
        paths["gaps"].write_text("0\n" * len(inputs))
        paths["ready"].write_text("1\n0\n0\n1\n1\n0\n1\n")
        testbench = run / "tb_stream_selfcheck.vhd"
        text = render_testbench(spec, paths, len(inputs), 2, 20)
        testbench.write_text(text.replace("port map (", f"generic map (fault_mode => {mode})\n    port map (", 1))
        runner = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = runner.run(description="Create CORDIC checker fixture:",
                source=root / "tests/fixtures/create_testbench_project.tcl",
                tclargs=[str(run), str(root / "tests/fixtures/ip/cordic/faulty_sqrt.vhd")],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            result = runner.run(description="Check CORDIC fixture:", source=root / "tcl/run_xsim_batch.tcl",
                tclargs=[str(run / "proj/framework_negative.xpr"), str(testbench), "tb_stream_selfcheck",
                         "AXIS_SELF_CHECK_STATUS: PASS", "AXIS_SELF_CHECK_STATUS: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
        self.assertEqual(result.returncode, 0 if mode == 0 else 1, result.output[-3000:])
        marker = ("AXIS_SELF_CHECK_STATUS: PASS" if not mode else "output changed under backpressure"
                  if mode in (2, 3) else "watchdog timeout" if mode == 4 else "extra output"
                  if mode == 5 else "payload mismatch")
        self.assertIn(marker, result.output)
        if not mode:
            self.assertEqual(paths["actual_output"].read_bytes(), paths["expected_output"].read_bytes())
            self.assertEqual(paths["accepted_input"].read_bytes(), paths["input_vectors"].read_bytes())

    def test_handwritten_probe_reproduces_nearest_even_difference(self):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        parameters = {**PARAMETERS, "rounding": "Nearest_Even", "has_last": False, "user_width": 0}
        spec = CordicPlugin(layout, create_default_strategy_registry()).describe(parameters)
        run = root / "runs/framework/protocol_probe" / layout.run_id / "cordic/nearest_even"
        logs = root / "runs/logs/framework/protocol_probe" / layout.run_id / "cordic/nearest_even"
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        source = root / "tests/fixtures/ip/cordic/nearest_even_probe.vhd"
        testbench = run / source.name
        testbench.write_bytes(source.read_bytes())
        (run / "parameters.json").write_text(json.dumps({"parameters": parameters,
            "testbench_sha256": sha256_file(testbench), "reference": "handwritten fixed input, no Python oracle"},
            indent=2) + "\n")
        runner = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = runner.run(description="Create CORDIC rounding probe:",
                source=root / "tcl/ip/cordic/create_ip.tcl",
                tclargs=[str(run), *(item for key, value in spec.settings.items()
                                    for item in (f"CONFIG.{key}", setting_text(value)))],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-3000:])
            result = runner.run(description="Run handwritten CORDIC probe:", source=root / "tcl/run_xsim_batch.tcl",
                tclargs=[str(run / "proj/ip_test.xpr"), str(testbench), "tb_cordic_probe",
                         "CORDIC_PROBE_STATUS: PASS", "CORDIC_PROBE_STATUS: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
        self.assertEqual(result.returncode, 0, result.output[-3000:])
        values = [(int(x), int(y)) for x, y in re.findall(r"CORDIC_SAMPLE input=(\d+) output=(\d+)", result.output)]
        self.assertEqual(len(values), 10)
        self.assertIn((7, 2), values)
        self.assertIn((255, 240), values)

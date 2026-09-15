from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout
from vivado_ip_test.plugins.axis_subset_converter.plugin import AxisSubsetConverterPlugin
from vivado_ip_test.plugins.common.stream.testbench import render_testbench
from vivado_ip_test.plugins.common.testbench import packed
from vivado_ip_test.strategies import create_default_strategy_registry


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class SubsetFailureDetectionTests(unittest.TestCase):
    def test_correct_mapping_and_packet_counter(self):
        self.run_fault(0, "control", "AXIS_SELF_CHECK_STATUS: PASS")

    def test_clock_counter_instead_of_handshake_counter(self):
        self.run_fault(1, "clock_count", "output changed under backpressure")

    def test_packet_counter_off_by_one(self):
        self.run_fault(2, "off_by_one", "payload mismatch")

    def test_swapped_data_fields(self):
        self.run_fault(3, "swap", "payload mismatch")

    def test_wrong_user_source(self):
        self.run_fault(4, "user", "payload mismatch")

    def test_packet_counter_stops_after_first_wrap(self):
        self.run_fault(5, "wrap", "payload mismatch")

    def run_fault(self, mode, name, marker):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        plugin = AxisSubsetConverterPlugin(layout, create_default_strategy_registry())
        parameters = {"input_bytes": 1, "output_bytes": 3, "input_user_width": 8, "output_user_width": 8,
            "input_id_width": 0, "output_id_width": 0, "input_dest_width": 0, "output_dest_width": 0,
            "input_has_keep": False, "output_has_keep": False, "input_has_strb": False, "output_has_strb": False,
            "input_has_last": False, "output_has_last": True, "mapping": "resize", "last_period": 3,
            "remap": {"tdata": "8'b10100101,tuser[7:0],tdata[7:0]", "tuser": "tdata[7:0]"}}
        spec = plugin.describe(parameters)
        run = root / "runs/framework/failure_detection" / layout.run_id / "axis_subset_converter" / name
        logs = root / "runs/logs/framework/failure_detection" / layout.run_id / "axis_subset_converter" / name
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        paths = {key: run / f"{key}.txt" for key in (
            "input_vectors", "expected_output", "actual_output", "gaps", "ready",
            "accepted_input", "protocol_events", "protocol_summary")}
        pairs = ((0x12, 0x89), (0x34, 0xAB), (0x56, 0xCD), (0, 255),
                 (255, 0), (0x80, 1), (7, 3), (0xAA, 0x55))
        frames = [dict(tdata=data, tuser=user) for data, user in pairs]
        expected = [dict(tdata=0xA50000 + user * 256 + data, tuser=data, tlast=int(i in (2, 5)))
                    for i, (data, user) in enumerate(pairs)]
        for key, values, ports in (("input_vectors", frames, spec.payload), ("expected_output", expected, spec.sink_payload)):
            paths[key].write_text("".join(packed(row, ports) + "\n" for row in values))
        paths["gaps"].write_text("0\n3\n1\n0\n4\n0\n2\n0\n")
        paths["ready"].write_text("1\n0\n0\n1\n1\n0\n1\n")
        testbench = run / "tb_stream_selfcheck.vhd"
        text = render_testbench(spec, paths, len(frames), 4, 20)
        testbench.write_text(text.replace("port map (", f"generic map (fault_mode => {mode})\n    port map (", 1))
        runner = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = runner.run(description="Create subset checker fixture:",
                source=root / "tests/fixtures/create_testbench_project.tcl",
                tclargs=[str(run), str(root / "tests/fixtures/ip/axis_subset_converter/faulty_subset.vhd")],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            result = runner.run(description="Run subset checker fixture:", source=root / "tcl/run_xsim_batch.tcl",
                tclargs=[str(run / "proj/framework_negative.xpr"), str(testbench), "tb_stream_selfcheck",
                         "AXIS_SELF_CHECK_STATUS: PASS", "AXIS_SELF_CHECK_STATUS: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
        self.assertEqual(result.returncode, 0 if mode == 0 else 1, result.output[-3000:])
        self.assertIn(marker, result.output)
        if mode == 0:
            self.assertEqual(paths["actual_output"].read_bytes(), paths["expected_output"].read_bytes())
            self.assertEqual(paths["accepted_input"].read_bytes(), paths["input_vectors"].read_bytes())

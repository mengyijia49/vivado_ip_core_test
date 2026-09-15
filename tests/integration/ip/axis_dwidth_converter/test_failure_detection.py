from contextlib import redirect_stdout
import io
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout
from vivado_ip_test.plugins.axis_dwidth_converter.plugin import AxisDwidthConverterPlugin
from vivado_ip_test.plugins.common.stream.byte_testbench import render_byte_testbench
from vivado_ip_test.plugins.common.stream.bytes import expected_bytes, raw_output_tokens
from vivado_ip_test.plugins.common.testbench import packed
from vivado_ip_test.strategies import create_default_strategy_registry


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class ByteStreamFailureDetectionTests(unittest.TestCase):
    def test_correct_control_with_null_and_position_unknown_data(self):
        self.run_fault(0, "control", "AXIS_SELF_CHECK_STATUS: PASS")

    def test_wrong_data(self):
        self.run_fault(1, "data", "token mismatch")

    def test_lost_packet_boundary(self):
        self.run_fault(2, "packet", "watchdog timeout")

    def test_wrong_byte_user(self):
        self.run_fault(3, "user", "token mismatch")

    def test_reserved_qualifier(self):
        self.run_fault(4, "reserved", "reserved byte qualifier")

    def test_unstable_qualified_byte(self):
        self.run_fault(5, "unstable", "output changed under backpressure")

    def test_extra_packet(self):
        self.run_fault(6, "extra", "extra byte or packet boundary")

    def test_output_without_accepted_input(self):
        self.run_fault(7, "early", "output before accepted input")

    def test_unknown_qualified_data(self):
        self.run_fault(8, "unknown", "unknown qualified output")

    def test_lost_position_byte(self):
        self.run_fault(9, "position", "token mismatch")

    def run_fault(self, mode, name, marker):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        plugin = AxisDwidthConverterPlugin(layout, create_default_strategy_registry())
        spec = plugin.describe({"input_bytes": 1, "output_bytes": 2, "id_width": 1,
            "dest_width": 1, "user_bits_per_byte": 2, "has_last": True, "has_keep": True, "has_strb": True})
        run = root / "runs/framework/failure_detection" / layout.run_id / "axis_dwidth_converter" / name
        logs = root / "runs/logs/framework/failure_detection" / layout.run_id / "axis_dwidth_converter" / name
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        paths = {key: run / f"{key}.txt" for key in (
            "input_vectors", "expected_output", "expected_mask", "required_inputs", "actual_output",
            "raw_output", "gaps", "ready", "accepted_input", "protocol_events", "protocol_summary")}
        frames = [
            dict(tdata=0x11, tkeep=1, tstrb=1, tlast=0, tid=1, tdest=0, tuser=1),
            dict(tdata=0x22, tkeep=1, tstrb=0, tlast=1, tid=1, tdest=0, tuser=2),
            dict(tdata=0xFF, tkeep=0, tstrb=0, tlast=0, tid=0, tdest=1, tuser=0),
            dict(tdata=0xAA, tkeep=0, tstrb=0, tlast=1, tid=0, tdest=1, tuser=0)]
        expected = expected_bytes(frames, spec.payload)
        expected_rows, expected_masks, required_inputs = zip(*expected)
        for key, rows, ports in (("input_vectors", frames, spec.payload),
                ("expected_output", expected_rows, expected.ports), ("expected_mask", expected_masks, expected.ports)):
            paths[key].write_text("".join(packed(row, ports) + "\n" for row in rows))
        paths["required_inputs"].write_text("".join(f"{n}\n" for n in required_inputs))
        paths["gaps"].write_text("0\n0\n0\n0\n")
        paths["ready"].write_text("1\n0\n1\n1\n")
        testbench = run / "tb_stream_selfcheck.vhd"
        text = render_byte_testbench(spec, paths, len(frames), expected.count,
                                     SimpleNamespace(max_gap_cycles=2), 20)
        testbench.write_text(text.replace("port map (", f"generic map (fault_mode => {mode})\n    port map (", 1))
        runner = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = runner.run(description="Create byte checker fixture:",
                source=root / "tests/fixtures/create_testbench_project.tcl",
                tclargs=[str(run), str(root / "tests/fixtures/ip/axis_dwidth_converter/faulty_width_stream.vhd")],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            result = runner.run(description="Run byte checker fixture:", source=root / "tcl/run_xsim_batch.tcl",
                tclargs=[str(run / "proj/framework_negative.xpr"), str(testbench), "tb_stream_selfcheck",
                         "AXIS_SELF_CHECK_STATUS: PASS", "AXIS_SELF_CHECK_STATUS: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
        self.assertEqual(result.returncode, 0 if mode == 0 else 1, result.output[-3000:])
        self.assertIn(marker, result.output)
        if mode == 0:
            self.assertEqual(paths["accepted_input"].read_bytes(), paths["input_vectors"].read_bytes())
            decoded = list(raw_output_tokens(paths["raw_output"], spec.sink_payload))
            self.assertEqual(len(decoded), expected.count)
            for actual, row, mask in zip(decoded, expected_rows, expected_masks):
                for a, e, m in zip(actual, packed(row, expected.ports), packed(mask, expected.ports)):
                    self.assertTrue(m == "0" or a == e)

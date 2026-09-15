from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import re
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout
from vivado_ip_test.plugins.axis_switch.plugin import AxisSwitchPlugin
from vivado_ip_test.plugins.axis_switch.render import render_testbench
from vivado_ip_test.plugins.axis_switch.testbench import write_vectors
from vivado_ip_test.services.stimulus_schedule import StimulusSchedule
from vivado_ip_test.strategies import create_default_strategy_registry
from vivado_ip_test.domain import VerificationProfile


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class SwitchFailureDetectionTests(unittest.TestCase):
    def test_correct_switch_allows_cross_output_reordering(self):
        self.run_fault(0, "control", "AXIS_SELF_CHECK_STATUS: PASS")

    def test_wrong_destination_port(self):
        self.run_fault(1, "wrong_route", "wrong output route|output before offered stream input")

    def test_corrupted_data(self):
        self.run_fault(2, "data", "payload or stream order mismatch")

    def test_missing_output(self):
        self.run_fault(3, "missing", "watchdog timeout")

    def test_repeated_output(self):
        self.run_fault(4, "duplicate", "output before offered stream input|payload or stream order mismatch")

    def test_corrupted_user(self):
        self.run_fault(5, "user", "payload or stream order mismatch")

    def test_unknown_valid(self):
        self.run_fault(6, "unknown_valid", "unknown output valid")

    def test_unstable_output(self):
        self.run_fault(7, "unstable", "output changed under backpressure")

    def test_corrupted_source_tag(self):
        self.run_fault(8, "source_tag", "output before offered stream input|payload or stream order mismatch")

    def test_decode_error_on_legal_input(self):
        self.run_fault(9, "decode_error", "decode error for legal input")

    def test_unknown_input_ready(self):
        self.run_fault(10, "unknown_ready", "unknown input ready")

    def test_corrupted_last(self):
        self.run_fault(11, "last", "payload or stream order mismatch")

    def test_corrupted_id(self):
        self.run_fault(12, "id", "payload or stream order mismatch")

    def test_output_without_input_acknowledgment(self):
        self.run_fault(13, "missing_ack", "output before input handshake")

    def run_fault(self, mode, name, marker):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        plugin = AxisSwitchPlugin(layout, create_default_strategy_registry())
        spec = plugin.describe(dict(inputs=2, outputs=2, data_bytes=1, user_width=4, id_width=2,
            dest_width=1, has_keep=False, has_strb=False, has_last=True, decoder_reg=False,
            output_reg=True, arbiter="fixed_priority", arbitrate_transfers=1,
            arbitrate_cycles=0, arbitrate_last=False, routing="balanced"))
        run = root / "runs/framework/failure_detection" / layout.run_id / "axis_switch" / name
        logs = root / "runs/logs/framework/failure_detection" / layout.run_id / "axis_switch" / name
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        frames, expected = [], []
        for index in range(8):
            frame, wanted = {}, {}
            for lane in range(2):
                payload = dict(tdata=(0x20+16*index)|lane, tlast=1,
                               tid=index % 4, tdest=index % 2, tuser=(3*index+lane) % 16)
                frame.update({f"s{lane:02d}_{k}": v for k, v in payload.items()})
                wanted.update({f"s{lane:02d}_{k}": v for k, v in {"route": index % 2, **payload}.items()})
            frames.append(frame)
            expected.append(wanted)
        profile = VerificationProfile("directed_random", "1.0", 2026, 8, ("port_boundaries",))
        schedules = [StimulusSchedule((0,)*8, tuple(range(8)), 8),
                     StimulusSchedule((0, 4, 0, 0, 5, 0, 2, 0), tuple(range(8)), 19)]
        paths, mapping, counts = write_vectors(run, spec, frames, expected, schedules, profile)
        paths["ready"].write_text("10\n"*16 + "11\n"*8 + "01\n"*4 + "11\n"*8)
        text = render_testbench(spec, paths, len(frames), counts, 8, 0)
        paths["testbench"].write_text(text.replace("port map (", f"generic map (fault_mode => {mode})\n    port map (", 1))
        runner = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = runner.run(description="Create switch checker fixture:",
                source=root / "tests/fixtures/create_testbench_project.tcl",
                tclargs=[str(run), str(root / "tests/fixtures/ip/axis_switch/faulty_switch.vhd")],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            result = runner.run(description="Run switch checker fixture:", source=root / "tcl/run_xsim_batch.tcl",
                tclargs=[str(run / "proj/framework_negative.xpr"), str(paths["testbench"]), "tb_stream_selfcheck",
                         "AXIS_SELF_CHECK_STATUS: PASS", "AXIS_SELF_CHECK_STATUS: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
        self.assertEqual(result.returncode, 0 if mode == 0 else 1, result.output[-3000:])
        self.assertRegex(result.output, marker)
        if mode == 0:
            self.assertEqual(paths["actual_output"].read_bytes(), paths["expected_output"].read_bytes())
            self.assertEqual(paths["accepted_input"].read_bytes(), paths["input_vectors"].read_bytes())
            transfers = re.findall(r"\d+ output=(\d+) vr=11 .* data=([01]+)", paths["protocol_events"].read_text())
            source_zero = [(int(branch), int(bits[:8], 2)) for branch, bits in transfers if int(bits[:8], 2) % 2 == 0]
            self.assertEqual(source_zero[0], (1, 0x30))
            self.assertIn((0, 0x20), source_zero)
            self.assertRegex(paths["protocol_summary"].read_text(), r"offered_contention_cycles=[1-9]")

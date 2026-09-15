from contextlib import redirect_stdout
from dataclasses import replace
import io
import os
from pathlib import Path
import re
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.domain import VerificationProfile
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout
from vivado_ip_test.plugins.axi_gpio.plugin import AxiGpioPlugin
from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.common.axilite.testbench import write_operations
from vivado_ip_test.plugins.common.cycle import DefinedBits
from vivado_ip_test.strategies import create_default_strategy_registry


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class AxiLiteFailureDetectionTests(unittest.TestCase):
    def test_control_accepts_independent_aw_and_w_handshakes(self):
        self.run_fault(0, "control", "AXILITE_SELF_CHECK_STATUS: PASS")

    def test_corrupted_data(self):
        self.run_fault(1, "data", "register or pin mismatches")

    def test_missing_write_response(self):
        self.run_fault(2, "missing_b", "write response timeout")

    def test_missing_read_response(self):
        self.run_fault(3, "missing_r", "read response timeout")

    def test_duplicate_write_response(self):
        self.run_fault(4, "duplicate_b", "write response without both requests")

    def test_duplicate_read_response(self):
        self.run_fault(5, "duplicate_r", "read response without request")

    def test_unstable_read_data(self):
        self.run_fault(6, "unstable_r", "read response changed under backpressure")

    def test_unstable_write_response(self):
        self.run_fault(7, "unstable_b", "write response changed under backpressure")

    def test_unknown_response_valid(self):
        self.run_fault(8, "unknown_bvalid", "unknown response valid")

    def test_unknown_read_data(self):
        self.run_fault(9, "unknown_rdata", "unknown read response")

    def test_bad_write_response_code(self):
        self.run_fault(10, "bad_bresp", "register or pin mismatches")

    def test_write_response_before_requests(self):
        self.run_fault(11, "early_b", "write response without both requests")

    def test_read_response_before_request(self):
        self.run_fault(12, "early_r", "read response without request")

    def test_reset_does_not_clear_register(self):
        self.run_fault(13, "reset", "register or pin mismatches")

    def test_gpio_incorrectly_uses_write_strobes(self):
        self.run_fault(14, "wstrb", "register or pin mismatches")

    def test_missing_interrupt(self):
        self.run_fault(15, "irq", "register or pin mismatches")

    def test_unknown_write_address_ready(self):
        self.run_fault(16, "unknown_awready", "unknown request ready")

    def test_read_valid_drops_under_backpressure(self):
        self.run_fault(17, "dropped_rvalid", "read response changed under backpressure")

    def test_bad_read_response_code(self):
        self.run_fault(18, "bad_rresp", "register or pin mismatches")

    def test_unknown_write_data_ready(self):
        self.run_fault(19, "unknown_wready", "unknown request ready")

    def test_unknown_read_address_ready(self):
        self.run_fault(20, "unknown_arready", "unknown request ready")

    def test_write_response_on_same_edge_as_last_request(self):
        self.run_fault(21, "same_edge_b", "write response without both requests")

    def test_read_response_on_same_edge_as_address(self):
        self.run_fault(22, "same_edge_r", "read response without request")

    def run_fault(self, mode, name, marker):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        plugin = AxiGpioPlugin(layout, create_default_strategy_registry())
        spec = plugin.describe(dict(channels=1, interrupt=True, width1=8, mode1="output",
            default_data1=0, default_tri1=0, width2=1, mode2="bidirectional",
            default_data2=0, default_tri2=1))
        run = root / "runs/framework/failure_detection" / layout.run_id / "axi_gpio" / name
        logs = root / "runs/logs/framework/failure_detection" / layout.run_id / "axi_gpio" / name
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        # Values are hand-calculated, independent of GpioModel and its operation generator.
        rows = [
            (Action.RESET, 0, 0, 0, 0, 0, 0),
            (Action.WRITE, 0, 0xA5, 0, 0, 0xA5, 0),
            (Action.READ, 0, 0, 0, 0xA5, 0xA5, 0),
            (Action.WRITE, 0, 0x5A, 2, 0, 0x5A, 0),
            (Action.READ, 0, 0, 0, 0x5A, 0x5A, 0),
            (Action.WRITE, 0x128, 1, 15, 0, 0x5A, 0),
            (Action.WRITE, 0x11C, 0x80000000, 15, 0, 0x5A, 0),
            (Action.WRITE, 0x120, 1, 15, 0, 0x5A, 1),
            (Action.READ, 0x120, 0, 0, 1, 0x5A, 1),
            (Action.WRITE, 0x120, 1, 15, 0, 0x5A, 0),
            (Action.READ, 0x120, 0, 0, 0, 0x5A, 0),
            (Action.RESET, 0, 0, 0, 0, 0, 0),
            (Action.READ, 0, 0, 0, 0, 0, 0),
        ]
        observations, operations = [], []
        for action, address, data, strobe, read_data, pins, irq in rows:
            operations.append({"command": dict(action=int(action), address=address, data=data, strobe=strobe)})
            observations.append(dict(response=0 if action in (Action.WRITE, Action.READ) else
                DefinedBits(0, 0, "no_bus_response"), read_data=read_data if action == Action.READ else
                DefinedBits(0, 0, "no_read_transfer"), gpio_io_o=pins, ip2intc_irpt=irq))

        class FixedOracle:
            def __init__(self):
                self.rows = iter(observations)

            def step(self, command):
                return next(self.rows)

        profile = VerificationProfile("directed_random", "1.0", 2026, len(rows), ("port_boundaries",))
        paths, _ = write_operations(run, replace(spec, model_factory=FixedOracle), operations, profile)
        text = paths["testbench"].read_text()
        paths["testbench"].write_text(text.replace("port map (", f"generic map (fault_mode => {mode})\n    port map (", 1))
        runner = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = runner.run(description="Create AXI-Lite checker fixture:",
                source=root / "tests/fixtures/create_testbench_project.tcl",
                tclargs=[str(run), str(root / "tests/fixtures/ip/axi_gpio/faulty_gpio.vhd")],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            result = runner.run(description="Run AXI-Lite checker fixture:", source=root / "tcl/run_xsim_batch.tcl",
                tclargs=[str(run / "proj/framework_negative.xpr"), str(paths["testbench"]), "tb_axilite_selfcheck",
                         "AXILITE_SELF_CHECK_STATUS: PASS", "AXILITE_SELF_CHECK_STATUS: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
        self.assertEqual(result.returncode, 0 if mode == 0 else 1, result.output[-3000:])
        self.assertRegex(result.output, marker)
        if mode == 0:
            self.assertEqual(paths["actual_output"].read_bytes(), paths["expected_output"].read_bytes())
            self.assertEqual(paths["accepted_input"].read_bytes(), paths["input_vectors"].read_bytes())
            trace = paths["protocol_events"].read_text().splitlines()
            self.assertTrue(any(" aw=11" in line and " w=11" not in line for line in trace))
            self.assertTrue(any(" w=11" in line and " aw=11" not in line for line in trace))
            summary = paths["protocol_summary"].read_text()
            self.assertIn("completed_writes=6", summary)
            self.assertIn("completed_reads=5", summary)
            self.assertRegex(summary, r"write_response_stall_cycles=[1-9]")
            self.assertRegex(summary, r"read_response_stall_cycles=[1-9]")

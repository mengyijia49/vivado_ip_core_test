from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.domain import VerificationProfile
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout, sha256_file
from vivado_ip_test.plugins.axi_timer.plugin import AxiTimerPlugin
from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.common.axilite.testbench import write_operations
from vivado_ip_test.plugins.common.cycle import DefinedBits
from vivado_ip_test.strategies import create_default_strategy_registry


@unittest.skipUnless(os.environ.get('VIVADO_INTEGRATION') == '1', '需显式启用真实 Vivado 集成测试')
class TimerFailureTests(unittest.TestCase):
    def test_control(self):
        self.run_fault(0, 'control', 'AXILITE_SELF_CHECK_STATUS: PASS')

    def test_wrong_count_step(self):
        self.run_fault(1, 'step', 'register or pin mismatches')

    def test_ignored_freeze(self):
        self.run_fault(2, 'freeze', 'register or pin mismatches')

    def test_wide_pulse(self):
        self.run_fault(3, 'wide_pulse', 'pulse wider than one clock')

    def test_missing_interrupt(self):
        self.run_fault(4, 'interrupt', 'register or pin mismatches')

    def test_missing_pulse(self):
        self.run_fault(5, 'missing_pulse', 'register or pin mismatches')

    def run_fault(self, mode, name, marker):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        run = root / 'runs/framework/failure_detection' / layout.run_id / 'axi_timer' / name
        logs = root / 'runs/logs/framework/failure_detection' / layout.run_id / 'axi_timer' / name
        report = root / 'reports/framework/failure_detection' / layout.run_id / 'axi_timer'
        for path in (run, logs, report):
            path.mkdir(parents=True)
        plugin = AxiTimerPlugin(layout, create_default_strategy_registry())
        spec = plugin.describe(dict(count_width=8, channels=1, trigger0_high=True,
            trigger1_high=True, generate0_high=True, generate1_high=True))
        # Hand-calculated observations, without TimerModel or the operation generator.
        rows = [
            (Action.RESET, 0, 0, 0, 0, 0, 0),
            (Action.WRITE, 4, 2, 0, 0, 0, 0),
            (Action.WRITE, 0, 0x20, 0, 0, 0, 0),
            (Action.WRITE, 0, 0xC4, 0, 0, 0, 0),
            (Action.WINDOW, 0, 0, 3, 0, 0, 0),
            (Action.READ, 8, 0, 0, 5, 0, 0),
            (Action.IDLE, 0, 0, 0, 0, 0, 0),
            (Action.READ, 8, 0, 0, 5, 0, 0),
            (Action.WRITE, 0, 0, 0, 0, 0, 0),
            (Action.WRITE, 4, 254, 0, 0, 0, 0),
            (Action.WRITE, 0, 0x20, 0, 0, 0, 0),
            (Action.WRITE, 0, 0xC4, 0, 0, 0, 0),
            (Action.WINDOW, 0, 0, 3, 0, 1, 1),
            (Action.READ, 8, 0, 0, 0, 1, 1),
            (Action.WRITE, 0, 0x1C4, 0, 0, 0, 1),
            (Action.RESET, 0, 0, 0, 0, 0, 1),
            (Action.READ, 8, 0, 0, 0, 0, 1),
        ]
        operations, observations = [], []
        for action, address, data, cycles, read, irq, pulses in rows:
            operations.append({'command': dict(action=int(action), address=address, data=data,
                strobe=15 if action == Action.WRITE else 0, run_cycles=cycles,
                capturetrig0=0, capturetrig1=0, freeze=1)})
            observations.append(dict(response=0 if action in (Action.WRITE, Action.READ) else
                DefinedBits(0, 0, 'no_bus_response'), read_data=read if action == Action.READ else
                DefinedBits(0, 0, 'no_read_transfer'), generateout0=0, generateout1=0, pwm0=0,
                interrupt=irq, generateout0_pulses=pulses, generateout1_pulses=0))

        class FixedOracle:
            def __init__(self):
                self.rows = iter(observations)

            def step(self, command):
                return next(self.rows)

        profile = VerificationProfile('directed_random', '1.0', 2026, len(rows), ('port_boundaries',))
        paths, _ = write_operations(run, replace(spec, model_factory=FixedOracle), operations, profile)
        paths['testbench'].write_text(paths['testbench'].read_text().replace('port map (',
            f'generic map (fault_mode => {mode})\n    port map (', 1))
        fixture = root / 'tests/fixtures/ip/axi_timer/faulty_timer.vhd'
        runner = VivadoBatchRunner(CommandRunner(), run / 'work')
        with redirect_stdout(io.StringIO()):
            created = runner.run(description='Create Timer checker fixture:',
                source=root / 'tests/fixtures/create_testbench_project.tcl', tclargs=[str(run), str(fixture)],
                log_path=logs / 'create.log', journal_path=logs / 'create.jou', timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            result = runner.run(description='Run Timer checker fixture:', source=root / 'tcl/run_xsim_batch.tcl',
                tclargs=[str(run / 'proj/framework_negative.xpr'), str(paths['testbench']),
                    'tb_axilite_selfcheck', 'AXILITE_SELF_CHECK_STATUS: PASS', 'AXILITE_SELF_CHECK_STATUS: FAIL'],
                log_path=logs / 'simulate.log', journal_path=logs / 'simulate.jou', timeout_sec=90)
        (report / 'summary.json').write_text(json.dumps({'run_id': layout.run_id, 'mode': mode,
            'name': name, 'artificial_fault_not_vendor_bug': True, 'returncode': result.returncode,
            'fixture_sha256': sha256_file(fixture), 'testbench_sha256': sha256_file(paths['testbench']),
            'expected_marker': marker, 'found_marker': marker in result.output}, indent=2) + '\n')
        self.assertEqual(result.returncode, 0 if mode == 0 else 1, result.output[-3000:])
        self.assertIn(marker, result.output)
        if mode == 0:
            self.assertEqual(paths['accepted_input'].read_bytes(), paths['input_vectors'].read_bytes())
            self.assertEqual(paths['actual_output'].read_bytes(), paths['expected_output'].read_bytes())

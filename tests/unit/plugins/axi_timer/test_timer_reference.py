from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.axilite.spec import Action, ClockWindow, PulseObservation
from vivado_ip_test.plugins.common.axilite.testbench import write_operations
from vivado_ip_test.plugins.common.axilite.render import _time_expression, render_testbench
from vivado_ip_test.plugins.axi_timer.reference import (
    TimerModel, ARHT, CAPT, ENALL, ENIT, ENT, GENT, LOAD, MDT, TINT, UDT)
from unit.plugins.cycle_helpers import plugin_case, ROOT


class TimerTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case('axi_timer')
        self.p = {**self.case.parameters, 'channels': 2}

    def command(self, action, address=0, data=0, cycles=0, trigger=0):
        return dict(action=int(action), address=address, data=data,
            strobe=15 if action == Action.WRITE else 0,
            capturetrig0=trigger, capturetrig1=0, freeze=1, run_cycles=cycles)

    def start(self, model, load, control, channel=0):
        model.write(channel*16, LOAD | TINT)
        model.write(channel*16+4, load)
        model.write(channel*16, control)

    def test_reset_load_width_readonly_and_all_strobes(self):
        for width in (8, 16, 32):
            for strobe in range(16):
                model = TimerModel({**self.p, 'count_width': width})
                command = self.command(Action.WRITE, 4, 0xFEDCBA98)
                command['strobe'] = strobe
                model.step(command)
                model.write(0, LOAD)
                wanted = 0xFEDCBA98 & ((1 << width)-1)
                self.assertEqual((model.load[0], model.count[0]), (wanted, wanted))
                model.write(8, 0)
                self.assertEqual(model.count[0], wanted)
                model.write(12, 0xFFFFFFFF)
                self.assertEqual(model.read(12), 0)
                model.reset()
                self.assertEqual((model.count, model.load, model.control), ([0, 0], [0, 0], [0, 0]))

    def test_up_down_windows_and_hold(self):
        model = TimerModel(self.p)
        self.start(model, 165, ENT)
        for n, wanted in ((1, 166), (2, 168), (3, 171), (4, 175)):
            model.advance(n)
            self.assertEqual(model.count[0], wanted)
        model.step(self.command(Action.IDLE))
        self.assertEqual(model.count[0], 175)
        model.write(0, 0)
        model.advance(20)
        self.assertEqual(model.count[0], 175)
        model.write(0, ENT | UDT)
        model.advance(6)
        self.assertEqual(model.count[0], 169)

    def test_one_shot_stops_after_rollover_even_after_irq_clear(self):
        for down, start, terminal in ((0, 252, 0), (UDT, 3, 255)):
            model = TimerModel(self.p)
            self.start(model, start, ENT | GENT | ENIT | down)
            model.advance(4)
            self.assertEqual(model.count[0], terminal)
            self.assertEqual(model.pulses[0], 1)
            self.assertTrue(model.control[0] & TINT)
            model.write(0, ENT | GENT | ENIT | down | TINT)
            model.advance(20)
            self.assertEqual(model.count[0], terminal)
            self.assertEqual(model.pulses[0], 1)
            self.assertFalse(model.control[0] & TINT)

    def test_continuous_reload_has_extra_cycle_and_settle_completes_pending_reload(self):
        model = TimerModel(self.p)
        self.start(model, 3, ENT | GENT | ARHT | UDT)
        model.advance(32)
        self.assertEqual((model.count[0], model.pulses[0]), (1, 6))
        self.start(model, 3, ENT | GENT | ARHT | UDT)
        for wanted in (2, 1, 0, 3, 2, 1, 0, 3):
            model.advance(1)
            self.assertEqual(model.count[0], wanted)
        self.assertEqual(model.pulses[0], 8)

    def test_capture_wrap_generates_pulse_but_not_interrupt(self):
        model = TimerModel(self.p)
        self.start(model, 254, MDT | ENT | ENIT | GENT)
        model.advance(4)
        self.assertEqual((model.count[0], model.pulses[0]), (2, 1))
        self.assertFalse(model.control[0] & TINT)

    def test_capture_hold_read_rearm_overwrite_and_polarity(self):
        for high in (False, True):
            for overwrite in (False, True):
                model = TimerModel({**self.p, 'trigger0_high': high})
                self.start(model, 64, ENT | MDT | CAPT | ENIT | (ARHT if overwrite else 0))
                model.read(4)
                active = self.command(Action.DRIVE, trigger=int(high))
                inactive = self.command(Action.DRIVE, trigger=1-int(high))
                model.step(active)
                model.advance(7)
                model.step(inactive)
                model.step(active)
                self.assertEqual(model.read(4), 71 if overwrite else 64)
                model.step(inactive)
                row = model.step(active)
                self.assertEqual(model.read(4), 71)
                self.assertEqual(row['interrupt'], 1)
                model.write(0, ENT | MDT | CAPT | TINT)
                self.assertFalse(model.control[0] & TINT)

    def test_enall_is_mirrored_and_clear_preserves_other_ent(self):
        model = TimerModel(self.p)
        self.start(model, 10, 0)
        self.start(model, 20, 0, 1)
        model.write(0, ENALL)
        self.assertEqual(model.control, [ENALL | ENT, ENALL | ENT])
        model.advance(7)
        self.assertEqual(model.count, [17, 27])
        model.write(0, ENT)
        self.assertEqual(model.control, [ENT, ENT])

    def test_masks_do_not_hide_counts_or_pulses(self):
        spec = self.plugin.describe(self.p)
        model = spec.model_factory()
        self.assertEqual(model.read(0).mask, 0xFFF)
        self.assertEqual(model.read(16).mask, 0x7FF)
        self.assertEqual(model.read(4), 0)
        self.assertEqual(model.read(8), 0)
        self.assertEqual([p.name for p in spec.observation.outputs[-2:]],
                         ['generateout0_pulses', 'generateout1_pulses'])
        self.assertNotIn('generateout0_pulses', [p.name for p in spec.outputs])

    def test_parameter_matrix_and_inactive_parameters(self):
        for changes in ({'count_width': True}, {'count_width': 9}, {'count_width': 24},
                        {'channels': 0}, {'trigger0_high': 1}, {'channels': 1, 'generate1_high': False}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                self.plugin.describe({**self.p, **changes})
        extended = load_test_cases(ROOT / 'configs/ip/axi_timer/extended.json')
        self.assertEqual(len(extended), 60)
        self.assertEqual(len({json.dumps(dict(c.parameters), sort_keys=True) for c in extended}), 60)
        for case in extended:
            self.plugin.validate_case(case)

    def test_invalid_windows_and_observations_are_rejected(self):
        spec = self.plugin.describe(self.p)
        command = self.command(Action.WINDOW, cycles=7)
        spec.validate_command(command)
        for changes in ({'freeze': 0}, {'run_cycles': 0}, {'run_cycles': 4096},
                        {'action': int(Action.IDLE)}, {'address': 4}, {'data': 1}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                spec.validate_command({**command, **changes})
        for changes in ({'window': ClockWindow('missing')}, {'window': ClockWindow('freeze', 2)},
                        {'pulses': (PulseObservation('missing'),)}, {'pulses': spec.pulses * 2}):
            with self.assertRaises(ValueError):
                replace(spec, **changes)

    def test_generation_includes_state_boundaries_and_auditable_windows(self):
        spec = self.plugin.describe(self.p)
        operations = spec.prepare_operations([])
        phases = {op['phase'] for op in operations}
        self.assertIn('timer0_capture', phases)
        self.assertIn('timer1_rollover_and_freeze', phases)
        self.assertIn('enable_all', phases)
        for address in (8, 24):
            self.assertTrue(any(op['command']['action'] == Action.WRITE and
                op['command']['address'] == address and op['command']['data'] == 0xFFFFFFFF for op in operations))
        with tempfile.TemporaryDirectory() as directory:
            paths, metrics = write_operations(Path(directory), spec, operations, self.case.verification)
            text = paths['testbench'].read_text()
            self.assertIn("p_freeze <= '0'", text)
            self.assertIn('pulse_monitor : process', text)
            self.assertIn('sampled request differs', text)
            self.assertGreater(metrics['requested_running_cycles'], 0)
            self.assertEqual(metrics['clock_window_count'], sum(op['command']['action'] == Action.WINDOW for op in operations))
            self.assertTrue(all(metrics['defined_output_bits_by_port'].values()))

    def test_unsupported_modes_fail_instead_of_silently_using_generate_reference(self):
        model = TimerModel(self.p)
        for control in (0x200, 0x800):
            with self.assertRaises(ValueError):
                model.write(0, control)

    def test_large_watchdog_uses_exact_physical_literals(self):
        for value, expected in ((0, '0 ns'), (2147483647, '2147483647 ns'),
                                (2147483648, '2 sec + 147483648 ns'),
                                (3748460790, '3 sec + 748460790 ns'),
                                (7492363040, '7 sec + 492363040 ns')):
            self.assertEqual(_time_expression(value), expected)
        for value in (True, -1, 1.2, 2147483648 * 1000000000):
            with self.assertRaises(ValueError):
                _time_expression(value)
        spec = self.plugin.describe(self.p)
        paths = {name: Path('/tmp/timer-watchdog')/name for name in
            ('input_vectors', 'expected_output', 'expected_mask', 'timing', 'actual_output',
             'accepted_input', 'mismatches', 'protocol_summary', 'protocol_events')}
        text = render_testbench(spec, paths, 128003, 64, {})
        self.assertRegex(text, r'wait for \d+ sec \+ \d+ ns;')

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout, sha256_file
from vivado_ip_test.plugins.common.metadata import load_metadata, setting_text
from vivado_ip_test.plugins.common.stream.testbench import render_testbench
from vivado_ip_test.plugins.common.testbench import packed
from vivado_ip_test.plugins.floating_point.plugin import FloatingPointPlugin
from vivado_ip_test.strategies import create_default_strategy_registry


PARAMETERS = {'operation': 'Float_to_fixed', 'input_exponent': 5, 'input_fraction': 11,
              'output_exponent': 4, 'output_fraction': 0, 'input_unsigned': False,
              'optimization': 'Resources', 'has_last': True, 'user_width': 3,
              'has_underflow': False, 'has_overflow': True, 'has_invalid_op': True}
INPUTS = (0x0000, 0x8000, 0x3c00, 0x4100, 0x4300, 0xc100, 0x4780, 0xc840,
          0xc880, 0x7c00, 0xfc00, 0x7c01, 0x7e00, 0xfc01, 0x03ff, 0x0400, 0x0001)
RESULTS = (0, 0, 1, 2, 4, 254, 7, 248, 248, 7, 248, 248, 248, 248, 0, 0, 0)
FLAGS = (0, 0, 0, 0, 0, 0, 1, 0, 1, 3, 3, 2, 2, 2, 0, 0, 0)


@unittest.skipUnless(os.environ.get('VIVADO_INTEGRATION') == '1', '需显式启用真实 Vivado 集成测试')
class FloatingFailureDetectionTests(unittest.TestCase):
    def test_control_and_ten_protocol_or_numeric_faults(self):
        names = ('control', 'rounding', 'unknown', 'unstable', 'drop', 'extra', 'last', 'user', 'padding', 'overflow', 'nan')
        for mode, name in enumerate(names):
            with self.subTest(name=name):
                self.run_fixture(mode, name)

    def run_fixture(self, mode, name):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        spec = FloatingPointPlugin(layout, create_default_strategy_registry()).describe(PARAMETERS)
        run = root / 'runs/framework/failure_detection' / layout.run_id / 'floating_point' / name
        logs = root / 'runs/logs/framework/failure_detection' / layout.run_id / 'floating_point' / name
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        paths = {key: run / f'{key}.txt' for key in ('input_vectors', 'expected_output', 'actual_output',
                 'gaps', 'ready', 'accepted_input', 'protocol_events', 'protocol_summary')}
        for key, values, ports in (('input_vectors', INPUTS, spec.payload), ('expected_output', RESULTS, spec.sink_payload)):
            rows = []
            for i, value in enumerate(values):
                user = i % 8 if key == 'input_vectors' else ((i % 8) << 2) | FLAGS[i]
                rows.append(packed({'tdata': value, 'tlast': i % 2, 'tuser': user}, ports))
            paths[key].write_text('\n'.join(rows) + '\n')
        paths['gaps'].write_text('0\n' * len(INPUTS))
        paths['ready'].write_text('1\n0\n0\n1\n1\n0\n1\n')
        testbench = run / 'tb_stream_selfcheck.vhd'
        text = render_testbench(spec, paths, len(INPUTS), 2, 20)
        testbench.write_text(text.replace('port map (', f'generic map (fault_mode => {mode})\n    port map (', 1))
        runner = VivadoBatchRunner(CommandRunner(), run / 'work')
        with redirect_stdout(io.StringIO()):
            created = runner.run(description='Create floating point checker fixture:',
                source=root / 'tests/fixtures/create_testbench_project.tcl',
                tclargs=[str(run), str(root / 'tests/fixtures/ip/floating_point/faulty_conversion.vhd')],
                log_path=logs / 'create.log', journal_path=logs / 'create.jou', timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            result = runner.run(description='Check floating point fixture:', source=root / 'tcl/run_xsim_batch.tcl',
                tclargs=[str(run / 'proj/framework_negative.xpr'), str(testbench), 'tb_stream_selfcheck',
                         'AXIS_SELF_CHECK_STATUS: PASS', 'AXIS_SELF_CHECK_STATUS: FAIL'],
                log_path=logs / 'simulate.log', journal_path=logs / 'simulate.jou', timeout_sec=90)
        self.assertEqual(result.returncode, 0 if mode == 0 else 1, result.output[-3000:])
        marker = ('AXIS_SELF_CHECK_STATUS: PASS' if not mode else 'output changed under backpressure'
                  if mode in (2, 3) else 'watchdog timeout' if mode == 4 else 'extra output'
                  if mode == 5 else 'payload mismatch')
        self.assertIn(marker, result.output)
        if not mode:
            self.assertEqual(paths['actual_output'].read_bytes(), paths['expected_output'].read_bytes())
            self.assertEqual(paths['accepted_input'].read_bytes(), paths['input_vectors'].read_bytes())

    def test_handwritten_real_ip_trace_without_python_reference(self):
        self.run_probe({**PARAMETERS, 'has_last': False, 'user_width': 0},
                       'fixed_conversion_probe.vhd', 'fixed_conversion', len(INPUTS))

    def test_handwritten_underflow_boundary_without_python_reference(self):
        self.run_probe({**PARAMETERS, 'operation': 'Float_to_float', 'input_exponent': 8,
            'input_fraction': 24, 'output_exponent': 5, 'output_fraction': 11,
            'has_underflow': True, 'has_invalid_op': False, 'has_last': False, 'user_width': 0},
            'underflow_probe.vhd', 'underflow_boundary', 14)

    def test_handwritten_square_root_at_parallel_and_serial_rates(self):
        for rate in (1, 12):
            with self.subTest(rate=rate):
                self.run_probe({**PARAMETERS, 'operation': 'Square_root', 'output_exponent': 5,
                    'output_fraction': 11, 'has_overflow': False, 'has_last': False, 'user_width': 0,
                    'cycles_per_operation': rate}, 'square_root_probe.vhd', f'square_root_rate{rate}', 22)

    def run_probe(self, parameters, filename, name, count):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        spec = FloatingPointPlugin(layout, create_default_strategy_registry()).describe(parameters)
        run = root / 'runs/framework/protocol_probe' / layout.run_id / 'floating_point' / name
        logs = root / 'runs/logs/framework/protocol_probe' / layout.run_id / 'floating_point' / name
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        source = root / 'tests/fixtures/ip/floating_point' / filename
        testbench = run / source.name
        testbench.write_bytes(source.read_bytes())
        (run / 'parameters.json').write_text(json.dumps({'parameters': parameters,
            'testbench_sha256': sha256_file(testbench), 'reference': 'literal VHDL trace, no Python oracle'}, indent=2) + '\n')
        runner = VivadoBatchRunner(CommandRunner(), run / 'work')
        with redirect_stdout(io.StringIO()):
            created = runner.run(description='Create floating point fixed conversion probe:',
                source=root / 'tcl/ip/floating_point/create_ip.tcl',
                tclargs=[str(run), *(item for key, value in spec.settings.items() for item in (f'CONFIG.{key}', setting_text(value)))],
                log_path=logs / 'create.log', journal_path=logs / 'create.jou', timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-3000:])
            load_metadata(run, spec, 'floating_point', '7.1')
            result = runner.run(description='Run literal floating point probe:', source=root / 'tcl/run_xsim_batch.tcl',
                tclargs=[str(run / 'proj/ip_test.xpr'), str(testbench), 'tb_floating_probe',
                         'FLOATING_PROBE_STATUS: PASS', 'FLOATING_PROBE_STATUS: FAIL'],
                log_path=logs / 'simulate.log', journal_path=logs / 'simulate.jou', timeout_sec=90)
        self.assertEqual(result.returncode, 0, result.output[-3000:])
        self.assertEqual(result.output.count('Note: FLOATING_SAMPLE '), count)

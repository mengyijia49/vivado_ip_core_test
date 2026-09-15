from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout, sha256_file
from vivado_ip_test.infrastructure.source_inventory import source_inventory
from vivado_ip_test.plugins.common.metadata import load_metadata, setting_text
from vivado_ip_test.plugins.common.testbench import packed
from vivado_ip_test.plugins.floating_point.arithmetic.spec import describe
from vivado_ip_test.plugins.floating_point.multi_input.testbench import render_testbench


PARAMETERS = {'operation': 'Add_Subtract', 'add_sub_value': 'Both', 'input_exponent': 4,
    'input_fraction': 4, 'optimization': 'Resources', 'architecture': 'Speed_Optimized',
    'mult_usage': 'No_Usage', 'has_underflow': True, 'has_overflow': True, 'has_invalid_op': True,
    'a_user_width': 3, 'b_user_width': 5, 'operation_user_width': 2, 'has_a_last': True,
    'has_b_last': True, 'has_operation_last': True, 'last_mode': 'Or'}
INPUTS = ((0, 128, 0), (128, 128, 0), (0x38, 0x38, 1), (0x38, 0x18, 0),
          (0x39, 0x18, 0), (0x3f, 0x18, 0), (0x77, 0x77, 0), (0x09, 0x08, 1),
          (0x78, 0xf8, 0), (0x78, 0x78, 1), (0x79, 0x38, 0), (1, 0xb8, 0))
RESULTS = (0, 0x80, 0, 0x38, 0x3a, 0x40, 0x78, 0, 0x7c, 0x7c, 0x7c, 0xb8)
FLAGS = (0, 0, 0, 0, 0, 0, 2, 1, 4, 4, 0, 0)


def archive_sources(root, run):
    sources = source_inventory(root)
    for path in (Path(__file__), root / 'tests/fixtures/create_testbench_project.tcl'):
        sources[str(path.relative_to(root))] = sha256_file(path)
    for relative in sources:
        target = run / 'source' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / relative, target)
    return sources


@unittest.skipUnless(os.environ.get('VIVADO_INTEGRATION') == '1', '需显式启用真实 Vivado 集成测试')
class ArithmeticFailureDetectionTests(unittest.TestCase):
    def test_handwritten_real_addition_without_python_reference(self):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        spec = describe(PARAMETERS)
        run = root / 'runs/framework/protocol_probe' / layout.run_id / 'floating_point/arithmetic'
        logs = root / 'runs/logs/framework/protocol_probe' / layout.run_id / 'floating_point/arithmetic'
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        sources = archive_sources(root, run)
        testbench = run / 'add_subtract_probe.vhd'
        shutil.copyfile(root / 'tests/fixtures/ip/floating_point/arithmetic/add_subtract_probe.vhd', testbench)
        (run / 'parameters.json').write_text(json.dumps({'parameters': PARAMETERS,
            'source_sha256': sources,
            'testbench_sha256': sha256_file(testbench),
            'reference': 'literal VHDL trace, no Python numeric model'}, indent=2) + '\n')
        runner = VivadoBatchRunner(CommandRunner(), run / 'work')
        with redirect_stdout(io.StringIO()):
            created = runner.run(description='Create addition probe:', source=run / 'source/tcl/ip/floating_point/create_ip.tcl',
                tclargs=[str(run), *(item for key, value in spec.settings.items()
                                    for item in (f'CONFIG.{key}', setting_text(value)))],
                log_path=logs / 'create.log', journal_path=logs / 'create.jou', timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-3000:])
            load_metadata(run, spec, 'floating_point', '7.1')
            result = runner.run(description='Run literal addition probe:', source=run / 'source/tcl/run_xsim_batch.tcl',
                tclargs=[str(run / 'proj/ip_test.xpr'), str(testbench), 'tb_floating_add_probe',
                         'FLOATING_ADD_PROBE_STATUS: PASS', 'FLOATING_ADD_PROBE_STATUS: FAIL'],
                log_path=logs / 'simulate.log', journal_path=logs / 'simulate.jou', timeout_sec=90)
        (run / 'result.json').write_text(json.dumps({'returncode': result.returncode,
            'expected_returncode': 0, 'samples': result.output.count('Note: FLOATING_ADD_SAMPLE ')}, indent=2) + '\n')
        self.assertEqual(result.returncode, 0, result.output[-3000:])
        self.assertEqual(result.output.count('Note: FLOATING_ADD_SAMPLE '), len(INPUTS))

    def test_independent_queues_and_thirteen_faults(self):
        names = ('control', 'numeric', 'user', 'last', 'unknown', 'unstable', 'drop', 'extra',
                 'early', 'valid_drop', 'unknown_ready', 'opcode', 'exception_flag', 'lost_operand')
        for mode, name in enumerate(names):
            with self.subTest(name=name):
                self.run_fixture(mode, name)

    def run_fixture(self, mode, name):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        spec = describe(PARAMETERS)
        run = root / 'runs/framework/failure_detection' / layout.run_id / 'floating_point' / f'arithmetic_{name}'
        logs = root / 'runs/logs/framework/failure_detection' / layout.run_id / 'floating_point' / f'arithmetic_{name}'
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        sources = archive_sources(root, run)
        paths = {key: run / f'{key}.txt' for key in ('input_vectors', 'expected_output', 'actual_output',
                 'gaps', 'ready', 'accepted_input', 'protocol_events', 'protocol_summary')}
        inputs, outputs = [], []
        for i, ((a, b, opcode), result) in enumerate(zip(INPUTS, RESULTS)):
            users = (i % 8, (3 * i) % 32, i % 4)
            lasts = tuple((i >> bit) & 1 for bit in range(3))
            frame = {'a_tdata': a, 'b_tdata': b, 'operation_tdata': opcode | ((i % 4) << 6)}
            for lane, user, last in zip(('a', 'b', 'operation'), users, lasts):
                frame.update({f'{lane}_tuser': user, f'{lane}_tlast': last})
            inputs.append(packed(frame, spec.payload))
            outputs.append(packed({'tdata': result, 'tuser': ((users[0] | users[1] << 3 | users[2] << 8) << 3) | FLAGS[i],
                                   'tlast': int(any(lasts))}, spec.sink_payload))
        paths['input_vectors'].write_text('\n'.join(inputs) + '\n')
        paths['expected_output'].write_text('\n'.join(outputs) + '\n')
        paths['gaps'].write_text('0 30 60\n' + '0 0 0\n' * (len(INPUTS) - 1))
        paths['ready'].write_text('1\n1\n0\n0\n1\n0\n1\n')
        testbench = run / 'tb_stream_selfcheck.vhd'
        text = render_testbench(spec, paths, len(INPUTS), 60, 0 if mode == 8 else 100)
        testbench.write_text(text.replace('port map (', f'generic map (fault_mode => {mode})\n    port map (', 1))
        fixture = run / 'faulty_arithmetic.vhd'
        shutil.copyfile(root / 'tests/fixtures/ip/floating_point/arithmetic/faulty_arithmetic.vhd', fixture)
        (run / 'parameters.json').write_text(json.dumps({'parameters': PARAMETERS, 'fault_mode': mode,
            'source_sha256': sources,
            'fixture_sha256': sha256_file(fixture), 'testbench_sha256': sha256_file(testbench),
            'reference': 'literal expected values, no Python numeric model'}, indent=2) + '\n')
        runner = VivadoBatchRunner(CommandRunner(), run / 'work')
        with redirect_stdout(io.StringIO()):
            created = runner.run(description='Create addition fixture:', source=run / 'source/tests/fixtures/create_testbench_project.tcl',
                tclargs=[str(run), str(fixture)], log_path=logs / 'create.log', journal_path=logs / 'create.jou', timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            result = runner.run(description='Check addition fixture:', source=run / 'source/tcl/run_xsim_batch.tcl',
                tclargs=[str(run / 'proj/framework_negative.xpr'), str(testbench), 'tb_stream_selfcheck',
                         'AXIS_SELF_CHECK_STATUS: PASS', 'AXIS_SELF_CHECK_STATUS: FAIL'],
                log_path=logs / 'simulate.log', journal_path=logs / 'simulate.jou', timeout_sec=90)
        (run / 'result.json').write_text(json.dumps({'returncode': result.returncode,
            'expected_returncode': 0 if mode == 0 else 1, 'injected_fault': name}, indent=2) + '\n')
        self.assertEqual(result.returncode, 0 if mode == 0 else 1, result.output[-3000:])
        marker = ('AXIS_SELF_CHECK_STATUS: PASS' if mode == 0 else 'watchdog timeout' if mode in (6, 13)
                  else 'extra output' if mode == 7 else 'before operand offered' if mode == 8
                  else 'unknown input ready' if mode == 10 else 'output changed under backpressure'
                  if mode in (4, 5, 9) else 'payload mismatch')
        self.assertIn(marker, result.output)
        if mode == 0:
            self.assertEqual(paths['actual_output'].read_bytes(), paths['expected_output'].read_bytes())
            self.assertEqual(paths['accepted_input'].read_bytes(), paths['input_vectors'].read_bytes())
            self.assertIn('max_accepted_operand_skew=4', paths['protocol_summary'].read_text())

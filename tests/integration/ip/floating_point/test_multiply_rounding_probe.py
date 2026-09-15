from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import shutil
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout, sha256_file
from vivado_ip_test.infrastructure.source_inventory import source_inventory
from vivado_ip_test.plugins.common.metadata import load_metadata, setting_text
from vivado_ip_test.plugins.floating_point.arithmetic.spec import describe


@unittest.skipUnless(os.environ.get('VIVADO_INTEGRATION') == '1', '需显式启用真实 Vivado 集成测试')
class MultiplyRoundingProbeTests(unittest.TestCase):
    def test_low_latency_max_dsp(self):
        self.run_probe('Low_Latency', 'Max_Usage')

    def test_speed_optimized_max_dsp(self):
        self.run_probe('Speed_Optimized', 'Max_Usage')

    def test_speed_optimized_no_dsp(self):
        self.run_probe('Speed_Optimized', 'No_Usage')

    def run_probe(self, architecture, mult_usage):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        run = root / 'runs/framework/floating_multiply_probe' / layout.run_id / 'floating_point'
        logs = root / 'runs/logs/framework/floating_multiply_probe' / layout.run_id / 'floating_point'
        report = root / 'reports/framework/floating_multiply_probe' / layout.run_id
        for directory in (run, logs, report):
            directory.mkdir(parents=True)
        parameters = {'operation': 'Multiply', 'input_exponent': 11, 'input_fraction': 53,
            'optimization': 'Performance', 'architecture': architecture, 'mult_usage': mult_usage,
            'a_user_width': 0, 'b_user_width': 0, 'operation_user_width': 0,
            'has_a_last': False, 'has_b_last': False, 'has_operation_last': False, 'last_mode': 'None',
            'has_underflow': True, 'has_overflow': True, 'has_invalid_op': True}
        spec = describe(parameters)
        fixture = root / 'tests/fixtures/ip/floating_point/arithmetic/multiply_rounding_probe.vhd'
        testbench = run / fixture.name
        shutil.copyfile(fixture, testbench)
        shutil.copyfile(Path(__file__), run / Path(__file__).name)
        (run / 'parameters.json').write_text(json.dumps(parameters, indent=2) + '\n')
        for relative in source_inventory(root):
            target = run / 'source' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        runner = VivadoBatchRunner(CommandRunner(), root)
        with redirect_stdout(io.StringIO()):
            created = runner.run(description='Create literal floating multiply probe:',
                source=run / 'source/tcl/ip/floating_point/create_ip.tcl', work_dir=run / 'work/create',
                tclargs=[str(run), *(item for key, value in spec.settings.items()
                                    for item in (f'CONFIG.{key}', setting_text(value)))],
                log_path=logs / 'create.log', journal_path=logs / 'create.jou', timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-3000:])
            xci, metadata = load_metadata(run, spec, 'floating_point', '7.1')
            result = runner.run(description='Run literal floating multiply probe:',
                source=run / 'source/tcl/run_xsim_batch.tcl', work_dir=run / 'work/simulate',
                tclargs=[str(run / 'proj/ip_test.xpr'), str(testbench), 'tb_floating_multiply_probe',
                         'FLOATING_MULTIPLY_PROBE_STATUS: PASS', 'FLOATING_MULTIPLY_PROBE_STATUS: FAIL'],
                log_path=logs / 'simulate.log', journal_path=logs / 'simulate.jou', timeout_sec=90)
        pattern = r'Note: FLOATING_MULTIPLY_SAMPLE (\d+) expected=(\S+) actual=(\S+) expected_flags=(\S+) flags=(\S+)'
        observations = [{'index': int(index), 'expected': expected, 'actual': actual,
                         'expected_flags': wanted_flags, 'actual_flags': flags}
                        for index, expected, actual, wanted_flags, flags in re.findall(pattern, result.output)]
        mismatches = [row for row in observations if row['expected'] != row['actual']
                      or row['expected_flags'] != row['actual_flags']]
        summary = {'run_id': layout.run_id, 'parameters': parameters, 'metadata': metadata,
            'reference': 'literal VHDL values, no Python numeric model',
            'returncode': result.returncode, 'observations': observations, 'mismatches': mismatches,
            'testbench_sha256': sha256_file(testbench), 'xci_sha256': sha256_file(xci),
            'source_sha256': {str(path.relative_to(run)): sha256_file(path) for path in sorted(run.rglob('*'))
                              if path.is_file() and (path == testbench or path.suffix == '.py' or run / 'source' in path.parents)}}
        (report / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        self.assertEqual(len(observations), 16, result.output[-3000:])
        self.assertEqual([row['index'] for row in observations], list(range(16)))
        self.assertEqual(result.returncode, 0, f'{report}: {mismatches}')

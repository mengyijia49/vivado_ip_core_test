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
from vivado_ip_test.plugins.floating_point.reciprocal.spec import describe


@unittest.skipUnless(os.environ.get('VIVADO_INTEGRATION') == '1', '需显式启用真实 Vivado 集成测试')
class ReciprocalRoundingProbeTests(unittest.TestCase):
    def test_single_precision_boundary(self):
        self.run_probe('single', 8, 24, 'tb_floating_reciprocal_single_probe',
                       {1: ('7E000001', '7E000000'), 4: ('FE000001', 'FE000000')})

    def test_double_precision_boundary(self):
        self.run_probe('double', 11, 53, 'tb_floating_reciprocal_double_probe',
                       {1: ('7FC0000000000001', '7FC0000000000000'),
                        4: ('FFC0000000000001', 'FFC0000000000000')})

    def run_probe(self, name, exponent, fraction, top, wanted_mismatches):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        run = root / 'runs/framework/floating_reciprocal_probe' / layout.run_id / 'floating_point' / name
        logs = root / 'runs/logs/framework/floating_reciprocal_probe' / layout.run_id / 'floating_point' / name
        report = root / 'reports/framework/floating_reciprocal_probe' / layout.run_id / name
        for directory in (run, logs, report):
            directory.mkdir(parents=True)
        parameters = {'operation': 'Reciprocal', 'input_exponent': exponent,
            'input_fraction': fraction, 'output_exponent': exponent, 'output_fraction': fraction,
            'optimization': 'Resources', 'has_last': False, 'user_width': 0,
            'has_underflow': True, 'has_overflow': False, 'has_invalid_op': False,
            'has_divide_by_zero': True}
        spec = describe(parameters)
        fixture = root / f'tests/fixtures/ip/floating_point/reciprocal/reciprocal_{name}_probe.vhd'
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
            created = runner.run(description='Create literal floating reciprocal probe:',
                source=run / 'source/tcl/ip/floating_point/create_ip.tcl', work_dir=run / 'work/create',
                tclargs=[str(run), *(item for key, value in spec.settings.items()
                                    for item in (f'CONFIG.{key}', setting_text(value)))],
                log_path=logs / 'create.log', journal_path=logs / 'create.jou', timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-3000:])
            xci, metadata = load_metadata(run, spec, 'floating_point', '7.1')
            result = runner.run(description='Run literal floating reciprocal probe:',
                source=run / 'source/tcl/run_xsim_batch.tcl', work_dir=run / 'work/simulate',
                tclargs=[str(run / 'proj/ip_test.xpr'), str(testbench), top,
                         'FLOATING_RECIPROCAL_STATUS: PASS', 'FLOATING_RECIPROCAL_STATUS: FAIL'],
                log_path=logs / 'simulate.log', journal_path=logs / 'simulate.jou', timeout_sec=90)
        pattern = (r'Note: FLOATING_RECIPROCAL_SAMPLE (\d+) expected=(\S+) actual=(\S+) '
                   r'expected_flags=(\S+) flags=(\S+)')
        observations = [{'index': int(index), 'expected': expected, 'actual': actual,
                         'expected_flags': wanted_flags, 'actual_flags': flags}
                        for index, expected, actual, wanted_flags, flags in re.findall(pattern, result.output)]
        mismatches = [row for row in observations if row['expected'] != row['actual']
                      or row['expected_flags'] != row['actual_flags']]
        summary = {'run_id': layout.run_id, 'parameters': parameters, 'metadata': metadata,
            'reference': 'literal VHDL values calculated from exact rational arithmetic',
            'returncode': result.returncode, 'observations': observations, 'mismatches': mismatches,
            'testbench_sha256': sha256_file(testbench), 'xci_sha256': sha256_file(xci),
            'log_sha256': {path.name: sha256_file(path) for path in logs.iterdir() if path.is_file()}}
        (report / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        self.assertEqual([row['index'] for row in observations], list(range(11)), result.output[-3000:])
        self.assertEqual(result.returncode, 1, f'{report}: expected the preserved rounding difference')
        self.assertEqual({row['index']: (row['expected'], row['actual']) for row in mismatches},
                         wanted_mismatches, report)
        self.assertTrue(all(row['expected_flags'] == row['actual_flags'] for row in observations), report)


if __name__ == '__main__':
    unittest.main()

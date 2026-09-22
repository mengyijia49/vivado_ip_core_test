import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest
from zipfile import ZipFile

from vivado_ip_test.infrastructure import RepositoryLayout, sha256_file


@unittest.skipUnless(os.environ.get('VIVADO_INTEGRATION') == '1', '需显式启用厂商模型测试')
class FirCmodelProbeTests(unittest.TestCase):
    def test_literal_full_precision(self):
        root = Path(__file__).resolve().parents[4]
        rid = RepositoryLayout(root).run_id
        run = root / 'runs/framework/fir_cmodel_probe' / rid / 'fir_compiler'
        logs = root / 'runs/logs/framework/fir_cmodel_probe' / rid / 'fir_compiler'
        report = root / 'reports/framework/fir_cmodel_probe' / rid
        for directory in (run, logs, report):
            directory.mkdir(parents=True)
        archive = Path('/data/Xilinx/2026.1/Vivado/data/ip/xilinx/fir_compiler_v7_2/cmodel/fir_compiler_v7_2_bitacc_cmodel_lin64.zip')
        vendor = run / 'vendor_model'
        vendor.mkdir()
        names = ('fir_compiler_v7_2_bitacc_cmodel.h', 'xip_common_bitacc_cmodel.h',
                 'xip_mpz_bitacc_cmodel.h', 'gmp.h', 'libgmp.so.11', 'libgmpxx.so.4',
                 'libIp_fir_compiler_v7_2_bitacc_cmodel.so')
        with ZipFile(archive) as bundle:
            for name in names:
                (vendor / name).write_bytes(bundle.read(name))
        fixture = root / 'tests/fixtures/ip/fir_compiler/full_precision_cmodel.c'
        source = run / fixture.name
        shutil.copyfile(fixture, source)
        shutil.copyfile(Path(__file__), run / Path(__file__).name)
        executable = run / 'probe'
        command = ['gcc', '-std=c11', '-Wall', '-Wextra', '-Werror', str(source), '-isystem', str(vendor),
                   '-L' + str(vendor), '-Wl,-rpath,' + str(vendor),
                   '-lIp_fir_compiler_v7_2_bitacc_cmodel', '-lm', '-o', str(executable)]
        compiled = subprocess.run(command, cwd=run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=60)
        (logs / 'compile.log').write_text(compiled.stdout)
        self.assertEqual(compiled.returncode, 0, compiled.stdout[-3000:])
        previous = os.environ.get('LD_LIBRARY_PATH', '')
        env = {**os.environ, 'LD_LIBRARY_PATH': str(vendor) + (':' + previous if previous else '')}
        result = subprocess.run([str(executable)], cwd=run, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=60)
        (logs / 'model.log').write_text(result.stdout)
        pattern = r'^FIR_CMODEL_SAMPLE (\d+) width=(\d+) index=(\d+) expected=(\S+) actual=(\S+)$'
        rows = [{'kind': int(kind), 'requested_accum_width': int(width), 'index': int(index),
                 'expected': expected, 'actual': actual}
                for kind, width, index, expected, actual in re.findall(pattern, result.stdout, re.MULTILINE)]
        configurations = [{'kind': int(kind), 'requested_accum_width': int(requested),
                           'accum_width': int(accum), 'output_width': int(output), 'fraction_width': int(fraction)}
            for kind, requested, accum, output, fraction in re.findall(
                r'^FIR_CMODEL_CONFIG (\d+) requested_accum=(\d+) accum=(\d+) output=(\d+) fraction=(\d+)$',
                result.stdout, re.MULTILINE)]
        summary = {'run_id': rid, 'returncode': result.returncode, 'observations': rows,
            'configurations': configurations,
            'model_version': re.findall(r'^FIR_CMODEL_VERSION (\S+)$', result.stdout, re.MULTILINE),
            'mismatches': [row for row in rows if row['expected'] != row['actual']],
            'reference': 'literal small integers exactly representable in binary64; no Python numeric model',
            'compile_command': command, 'model_archive': str(archive), 'model_sha256': sha256_file(archive),
            'source_sha256': {str(path.relative_to(root)): sha256_file(path) for path in (Path(__file__), fixture)},
            'artifact_sha256': {str(path.relative_to(run)): sha256_file(path) for path in run.rglob('*') if path.is_file()},
            'log_sha256': {path.name: sha256_file(path) for path in logs.iterdir() if path.is_file()}}
        (report / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        self.assertEqual([(row['kind'], row['requested_accum_width'], row['index']) for row in rows],
                         [(kind, width, i) for kind, sufficient in enumerate((12, 11, 10))
                          for width in (0, sufficient) for i in range(16)], result.stdout)
        self.assertEqual(len(configurations), 6, result.stdout)
        self.assertFalse(summary['mismatches'], str(report))
        self.assertEqual(result.returncode, 0, f'{report}: {summary["mismatches"]}')

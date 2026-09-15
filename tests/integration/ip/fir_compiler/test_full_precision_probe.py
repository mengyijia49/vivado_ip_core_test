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


@unittest.skipUnless(os.environ.get('VIVADO_INTEGRATION') == '1', '需显式启用真实 Vivado 集成测试')
class FirFullPrecisionProbeTests(unittest.TestCase):
    def test_negative_power(self):
        self.run_probe(0, '-8,0,0', 11)

    def test_all_negative(self):
        self.run_probe(1, '-1,-1,-2', 10)

    def test_positive_control(self):
        self.run_probe(2, '1,1,2', 10)

    def test_negative_power_transpose(self):
        self.run_probe(0, '-8,0,0', 11, 'Transpose_Multiply_Accumulate')

    def test_all_negative_transpose(self):
        self.run_probe(1, '-1,-1,-2', 10, 'Transpose_Multiply_Accumulate')

    def test_positive_control_transpose(self):
        self.run_probe(2, '1,1,2', 10, 'Transpose_Multiply_Accumulate')

    def run_probe(self, kind, coefficients, output_width, architecture='Systolic_Multiply_Accumulate'):
        root = Path(__file__).resolve().parents[4]
        rid = RepositoryLayout(root).run_id
        run = root / 'runs/framework/fir_full_precision_probe' / rid / 'fir_compiler'
        logs = root / 'runs/logs/framework/fir_full_precision_probe' / rid / 'fir_compiler'
        reports = root / 'reports/framework/fir_full_precision_probe' / rid
        for directory in (run, logs, reports):
            directory.mkdir(parents=True)
        settings = {'Filter_Type': 'Single_Rate', 'DataCoefficientType': 'Real',
            'CoefficientSource': 'Vector', 'Coefficient_Sets': 1, 'Coefficient_Reload': False,
            'Coefficient_Structure': 'Non_Symmetric', 'Quantization': 'Integer_Coefficients',
            'Data_Sign': 'Signed', 'Data_Width': 8,
            'Coefficient_Sign': 'Signed' if any(int(value) < 0 for value in coefficients.split(',')) else 'Unsigned',
            'Coefficient_Width': 4,
            'CoefficientVector': coefficients, 'Output_Rounding_Mode': 'Full_Precision',
            'Filter_Architecture': architecture, 'Number_Channels': 1, 'Number_Paths': 1,
            'RateSpecification': 'Input_Sample_Period', 'SamplePeriod': 1, 'M_DATA_Has_TREADY': True,
            'S_DATA_Has_FIFO': True, 'Has_ARESETn': True, 'Reset_Data_Vector': True, 'Has_ACLKEN': False,
            'DATA_Has_TLAST': 'Packet_Framing', 'S_DATA_Has_TUSER': 'User_Field',
            'M_DATA_Has_TUSER': 'User_Field', 'DATA_TUSER_Width': 7}
        sources = source_inventory(root)
        fixture = root / 'tests/fixtures/ip/fir_compiler/full_precision_probe.vhd'
        for path in (Path(__file__), fixture):
            sources[str(path.relative_to(root))] = sha256_file(path)
        for relative in sources:
            target = run / 'source' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        testbench = run / fixture.name
        testbench.write_text(fixture.read_text().replace('constant kind : natural := 0;',
                                                       f'constant kind : natural := {kind};'))
        (run / 'parameters.json').write_text(json.dumps({'settings': settings, 'kind': kind}, indent=2) + '\n')
        runner = VivadoBatchRunner(CommandRunner(), run / 'work')
        with redirect_stdout(io.StringIO()):
            created = runner.run(description='Create FIR full precision probe:',
                source=run / 'source/tcl/diagnostics/inspect_ip.tcl',
                tclargs=[str(run), 'fir_compiler', *(value for key, raw in settings.items()
                    for value in ('CONFIG.' + key, str(raw).lower() if isinstance(raw, bool) else str(raw)))],
                log_path=logs / 'create.log', journal_path=logs / 'create.jou', timeout_sec=120)
            self.assertEqual(created.returncode, 0, created.output[-3000:])
            xci = run / 'proj/ip_probe.srcs/sources_1/ip/probe_0/probe_0.xci'
            instance = json.loads(xci.read_text())['ip_inst']
            self.assertEqual(instance['component_reference'], 'xilinx.com:ip:fir_compiler:7.2')
            for key, raw in settings.items():
                self.assertEqual(str(instance['parameters']['component_parameters'][key][0]['value']).lower(),
                                 str(raw).lower(), key)
            self.assertEqual(int(instance['parameters']['model_parameters']['C_OUTPUT_WIDTH'][0]['value']), output_width)
            result = runner.run(description='Run literal FIR full precision probe:',
                source=run / 'source/tcl/run_xsim_batch.tcl',
                tclargs=[str(run / 'proj/ip_probe.xpr'), str(testbench), 'tb_fir_full_precision_probe',
                         'FIR_FULL_PRECISION_STATUS: PASS', 'FIR_FULL_PRECISION_STATUS: FAIL'],
                log_path=logs / 'simulate.log', journal_path=logs / 'simulate.jou', timeout_sec=120)
        observations = [{'index': int(i), 'expected': int(wanted), 'actual': int(actual)}
            for i, wanted, actual in re.findall(r'Note: FIR_FULL_PRECISION_SAMPLE (\d+) expected=(-?\d+) actual=(-?\d+)', result.output)]
        summary = {'run_id': rid, 'settings': settings, 'kind': kind, 'returncode': result.returncode,
            'observations': observations, 'mismatches': [row for row in observations if row['expected'] != row['actual']],
            'reference': 'literal VHDL values, no Python numeric model',
            'xci_sha256': sha256_file(xci), 'testbench_sha256': sha256_file(testbench),
            'source_sha256': sources, 'ports': instance['boundary']['ports'],
            'component_parameters': instance['parameters']['component_parameters'],
            'model_parameters': instance['parameters']['model_parameters'],
            'log_sha256': {path.name: sha256_file(path) for path in logs.iterdir() if path.is_file()}}
        (reports / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        self.assertEqual([row['index'] for row in observations], list(range(16)), result.output[-3000:])
        self.assertEqual(result.returncode, 0, f'{reports}: {summary["mismatches"]}')

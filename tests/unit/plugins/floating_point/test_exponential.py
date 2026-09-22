from dataclasses import replace
import json
import math
from pathlib import Path
import random
import struct
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from vivado_ip_test.plugins.floating_point.transcendental.reference import calculate, expected_transactions
from vivado_ip_test.plugins.floating_point.transcendental.spec import describe
from vivado_ip_test.plugins.floating_point.transcendental.vectors import directed_values, prepare_frames
from vivado_ip_test.plugins.floating_point.accuracy import transcendental_tolerances
from unit.plugins.cycle_helpers import ROOT, plugin_case


def parameters(**changes):
    return {'operation':'Exponential','input_exponent':8,'input_fraction':24,
        'output_exponent':8,'output_fraction':24,'optimization':'Resources',
        'has_last':False,'user_width':0,'has_underflow':True,'has_overflow':True,
        'has_invalid_op':False,'has_divide_by_zero':False, **changes}


class ExponentialTests(unittest.TestCase):
    def test_known_values_specials_and_flags(self):
        fmt = FloatFormat(8, 24)
        for bits, wanted, active in (
            (0,0x3f800000,None),(0x80000000,0x3f800000,None),
            (0x3f800000,0x402df854,None),(0xbf800000,0x3ebc5ab2,None),
            (0x7f800000,0x7f800000,None),(0xff800000,0,None),
            (0x7f800001,0x7fc00000,None),(0x42b40000,0x7f800000,'overflow'),
            (0xc2d00000,0,'underflow')):
            value, flags = calculate(bits, 'Exponential', fmt, fmt)
            self.assertLessEqual(abs(value - wanted), 1)
            self.assertEqual([name for name, flag in flags.items() if flag],
                             [] if active is None else [active])

    def test_random_single_results_are_within_one_ulp_of_host_math(self):
        fmt = FloatFormat(8, 24)
        rng = random.Random(20261151)
        for _ in range(500):
            number = rng.uniform(-80, 80)
            bits = struct.unpack('>I', struct.pack('>f', number))[0]
            source = struct.unpack('>f', struct.pack('>I', bits))[0]
            wanted = struct.unpack('>I', struct.pack('>f', math.exp(source)))[0]
            actual, _ = calculate(bits, 'Exponential', fmt, fmt)
            self.assertLessEqual(abs(actual - wanted), 1)

    def test_spec_vectors_sidebands_tolerance_and_rejections(self):
        p = parameters(has_last=True, user_width=3)
        spec = describe(p)
        self.assertEqual(spec.settings['Operation_Type'], 'Exponential')
        self.assertEqual(spec.model_parameters['C_HAS_EXPONENTIAL'], 1)
        self.assertEqual(spec.model_parameters['C_HAS_LOGARITHM'], 0)
        self.assertIsNone(spec.input_reset)
        output = expected_transactions([{'tdata':0x3f800000,'tlast':1,'tuser':5}], p)[0]
        self.assertEqual(output['tlast'], 1)
        self.assertEqual(output['tuser'], 20)
        rows = prepare_frames([], spec, p)
        self.assertGreater(len(directed_values(p)), 150)
        self.assertEqual({row['tlast'] for row in rows}, {0,1})
        tolerances = list(transcendental_tolerances(
            [{'tdata':0}], [{'tdata':0x3f800000,'tlast':1,'tuser':20}], p))
        self.assertEqual(tolerances, [{'tdata':1,'tlast':0,'tuser':0}])
        for changes in ({'input_exponent':6},{'output_fraction':53},
                        {'has_invalid_op':True},{'has_divide_by_zero':True},
                        {'user_width':257},{'cycles_per_operation':2}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                describe(parameters(**changes))

    def test_generation_schema_and_96_matrix_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, base = plugin_case('floating_point', Path(directory))
            case = replace(base, case_id='exponential_fixture', parameters=parameters(),
                verification=replace(base.verification, strategy='directed_random', case_budget=512,
                                     coverage_targets=('port_boundaries',)))
            xci = Path(directory) / 'fake.xci'
            xci.write_text('{}')
            with patch('vivado_ip_test.plugins.common.stream.testbench.load_metadata',
                       return_value=(xci, {})):
                artifacts = plugin.generate_testbench(case)
            self.assertEqual(artifacts.metrics['reference_contract']['arithmetic'],
                             'decimal_high_precision_stable_encoding')
            self.assertEqual(artifacts.metrics['comparison_kind'],
                             'accepted_axis_payload_bounded_distance')
        schema = json.loads((ROOT / 'configs/schemas/ip/floating_point/exponential.schema.json').read_text())
        self.assertEqual(set(schema['required']), set(parameters()))
        cases = load_test_cases(ROOT / 'configs/ip/floating_point/matrices/exponential.json')
        self.assertEqual(len(cases), 96)
        self.assertEqual(len({tuple(sorted(case.parameters.items())) for case in cases}), 96)
        for case in cases:
            describe(case.parameters)


if __name__ == '__main__':
    unittest.main()

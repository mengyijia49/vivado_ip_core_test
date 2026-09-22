import math
import random
import struct
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from vivado_ip_test.plugins.floating_point.transcendental.reference import calculate, expected_transactions
from vivado_ip_test.plugins.floating_point.transcendental.spec import describe
from vivado_ip_test.plugins.floating_point.transcendental.vectors import directed_values
from unit.plugins.cycle_helpers import ROOT


def parameters(**changes):
    return {'operation':'Logarithm','input_exponent':8,'input_fraction':24,
        'output_exponent':8,'output_fraction':24,'optimization':'Resources',
        'has_last':False,'user_width':0,'has_underflow':False,'has_overflow':False,
        'has_invalid_op':True,'has_divide_by_zero':True, **changes}


class LogarithmTests(unittest.TestCase):
    def test_known_values_specials_and_flags(self):
        fmt = FloatFormat(8, 24)
        for bits, wanted, active in (
            (0,0xff800000,'divide_by_zero'),(0x80000000,0xff800000,'divide_by_zero'),
            (1,0xff800000,'divide_by_zero'),(0x3f800000,0,None),
            (0x40000000,0x3f317218,None),(0xbf800000,0x7fc00000,'invalid_op'),
            (0x7f800000,0x7f800000,None),(0xff800000,0x7fc00000,'invalid_op'),
            (0x7f800001,0x7fc00000,None)):
            value, flags = calculate(bits, 'Logarithm', fmt, fmt)
            self.assertLessEqual(abs(value - wanted), 1)
            self.assertEqual([name for name, flag in flags.items() if flag],
                             [] if active is None else [active])

    def test_random_single_results_are_within_one_ulp_of_host_math(self):
        fmt = FloatFormat(8, 24)
        rng = random.Random(20261161)
        for _ in range(500):
            number = 2.0 ** rng.uniform(-120, 120)
            bits = struct.unpack('>I', struct.pack('>f', number))[0]
            source = struct.unpack('>f', struct.pack('>I', bits))[0]
            wanted = struct.unpack('>I', struct.pack('>f', math.log(source)))[0]
            actual, _ = calculate(bits, 'Logarithm', fmt, fmt)
            self.assertLessEqual(abs(actual - wanted), 1)

    def test_spec_sidebands_rejections_and_96_matrix_cases(self):
        p = parameters(has_last=True, user_width=3)
        spec = describe(p)
        self.assertEqual(spec.settings['Operation_Type'], 'Logarithm')
        self.assertEqual(spec.model_parameters['C_HAS_LOGARITHM'], 1)
        self.assertEqual(spec.model_parameters['C_HAS_EXPONENTIAL'], 0)
        output = expected_transactions([{'tdata':0,'tlast':1,'tuser':5}], p)[0]
        self.assertEqual(output, {'tdata':0xff800000,'tlast':1,'tuser':22})
        self.assertGreater(len(directed_values(p)), 140)
        for changes in ({'input_fraction':11},{'output_exponent':11,'output_fraction':53},
                        {'has_underflow':True},{'has_overflow':True},{'has_invalid_op':1}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                describe(parameters(**changes))
        cases = load_test_cases(ROOT / 'configs/ip/floating_point/matrices/logarithm.json')
        self.assertEqual(len(cases), 96)
        self.assertEqual(len({tuple(sorted(case.parameters.items())) for case in cases}), 96)
        for case in cases:
            describe(case.parameters)


if __name__ == '__main__':
    unittest.main()

from dataclasses import replace
import json
import sys
import unittest

from vivado_ip_test.domain.counts import count_for_report
from vivado_ip_test.plugins.common.cycle import Port
from vivado_ip_test.plugins.common.vectors import port_space
from vivado_ip_test.strategies import create_default_strategy_registry
from vivado_ip_test.strategies.base import GenerationResult, StrategyError
from vivado_ip_test.strategies.coverage import measure_coverage
from unit.plugins.cycle_helpers import plugin_case


class LargeCountTests(unittest.TestCase):
    def test_small_counts_stay_numeric_and_large_counts_roundtrip(self):
        limit = sys.get_int_max_str_digits()
        for value in (0, 1, 100, 1 << 4096):
            self.assertEqual(json.loads(json.dumps(count_for_report(value))), value)
            self.assertIs(type(count_for_report(value)), int)
        encoded = json.loads(json.dumps(count_for_report(1 << 65536)))
        self.assertEqual(int(encoded, 16), 1 << 65536)
        self.assertEqual(sys.get_int_max_str_digits(), limit)
        for bad in (-1, True, "1", 1.0):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                count_for_report(bad)

    def test_coverage_preserves_exact_space_and_marks_fraction_underflow(self):
        space = port_space(tuple(Port(f"u{i}", 4096) for i in range(16)), False)
        result = GenerationResult(cases=(tuple(0 for _ in range(16)),), strategy="test",
                                  strategy_version="1", directed_count=1, generated_count=1)
        measured = measure_coverage(space, result, ("port_boundaries", "complete_input_space"))
        report = json.loads(json.dumps(measured.as_dict()))
        self.assertEqual(int(report["input_space_size"], 16), 1 << 65536)
        self.assertEqual(report["input_space_fraction"], 0.0)
        self.assertTrue(report["input_space_fraction_underflow"])
        complete = report["target_coverage"]["complete_input_space"]
        self.assertEqual(complete["hit_count"], 1)
        self.assertTrue(complete["fraction_underflow"])
        self.assertNotIn("fraction_underflow", report["target_coverage"]["port_boundaries"])

    def test_zero_hits_are_not_underflow(self):
        space = port_space((Port("a", 8),), False)
        result = GenerationResult(cases=((17,),), strategy="test", strategy_version="1",
                                  directed_count=0, generated_count=1)
        report = measure_coverage(space, result, ("port_boundaries",)).as_dict()
        bins = report["target_coverage"]["port_boundaries"]
        self.assertEqual(bins["fraction"], 0)
        self.assertNotIn("fraction_underflow", bins)

    def test_large_exhaustive_rejection_is_strategy_error_not_conversion_error(self):
        _, case = plugin_case("axis_combiner")
        space = port_space(tuple(Port(f"u{i}", 4096) for i in range(16)), False)
        with self.assertRaisesRegex(StrategyError, "0x1"):
            create_default_strategy_registry().generate(space, replace(case.verification, strategy="exhaustive"))

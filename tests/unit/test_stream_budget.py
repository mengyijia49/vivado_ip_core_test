from dataclasses import replace
import unittest
from unittest.mock import patch

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import Port
from vivado_ip_test.plugins.common.stream.plugin import _budget_bounds
from vivado_ip_test.plugins.common.vectors import port_space
from unit.plugins.cycle_helpers import plugin_case


class StreamBudgetTests(unittest.TestCase):
    def setUp(self):
        _budget_bounds.cache_clear()

    def tearDown(self):
        _budget_bounds.cache_clear()

    def test_cached_counts_equal_actual_case_spaces(self):
        for ports in ((), (Port('data', 1),), (Port('data', 80),),
                      (Port('data', 8), Port('user', 256)),
                      (Port('data', 7, maximum=9), Port('enable', scalar=True)),
                      (Port('a', scalar=True), Port('b', scalar=True))):
            for systematic in (False, True):
                with self.subTest(ports=ports, systematic=systematic):
                    space = port_space(ports, systematic)
                    self.assertEqual(_budget_bounds(ports, systematic),
                                     (len(space.directed_cases), space.total_case_count))

    def test_equal_ports_share_counts_but_different_limits_and_modes_do_not(self):
        with patch('vivado_ip_test.plugins.common.stream.plugin.port_space', wraps=port_space) as build:
            for _ in range(3):
                _budget_bounds((Port('data', 8),), True)
            self.assertEqual(build.call_count, 1)
            for ports, mode in (((Port('data', 8, maximum=100),), True),
                                ((Port('data', 8),), False), ((Port('user', 8),), True),
                                ((Port('data', 8, scalar=True),), True)):
                _budget_bounds(ports, mode)
            self.assertEqual(build.call_count, 5)
        self.assertEqual(_budget_bounds.cache_info().hits, 2)

    def test_cache_is_bounded_and_returns_only_integer_counts(self):
        for index in range(600):
            result = _budget_bounds((Port(f'port_{index}', 8),), True)
            self.assertTrue(all(type(value) is int for value in result))
        self.assertEqual(_budget_bounds.cache_info().currsize, 512)

    def test_cache_does_not_bypass_budget_or_parameter_validation(self):
        plugin, case = plugin_case('floating_point')
        plugin.validate_case(case)
        for strategy, budget in (('exhaustive', 255), ('directed_random', 1), ('directed_random', 257)):
            with self.subTest(strategy=strategy, budget=budget), self.assertRaises(PluginError):
                plugin.validate_case(replace(case, verification=replace(
                    case.verification, strategy=strategy, case_budget=budget)))
        with self.assertRaises(PluginError):
            plugin.validate_case(replace(case, parameters={**case.parameters, 'input_exponent': True}))

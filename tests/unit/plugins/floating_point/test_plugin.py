from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.infrastructure import RepositoryLayout
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.stream.testbench import render_testbench
from vivado_ip_test.plugins.floating_point.plugin import FloatingPointPlugin
from vivado_ip_test.strategies import create_default_strategy_registry
from unit.plugins.cycle_helpers import plugin_case, ROOT


class FloatingPluginTests(unittest.TestCase):
    def test_all_regression_cases_validate_and_absolute_has_no_clock(self):
        plugin, case = plugin_case('floating_point')
        for configured in load_test_cases(ROOT / 'configs/ip/floating_point/regression.json'):
            plugin.validate_case(configured)
        spec = plugin.describe(case.parameters)
        self.assertIsNone(spec.input_clock)
        self.assertIsNone(spec.input_reset)
        self.assertNotIn('aclk', {port.name for port in spec.inputs})
        paths = {name: Path('/tmp') / name for name in ('input_vectors', 'gaps', 'ready', 'accepted_input',
                 'expected_output', 'actual_output', 'protocol_events', 'protocol_summary')}
        rendered = render_testbench(spec, paths, 10, 8, 100)
        self.assertNotIn('None =>', rendered)
        self.assertNotIn('aclk =>', rendered)
        self.assertIn('s_axis_a_tvalid => s_valid', rendered)
        self.assertIn('m_axis_result_tdata => m_tdata', rendered)

    def test_unsupported_formats_operations_and_flags_are_rejected(self):
        plugin, case = plugin_case('floating_point')
        for change in ({'input_exponent': True}, {'input_fraction': 65}, {'input_unsigned': True},
                       {'has_overflow': True}, {'operation': 'Multiply'}, {'output_fraction': 5},
                       {'input_exponent': 4, 'input_fraction': 64}, {'user_width': 257},
                       {'latency': 0}, {'flow_control': 'NonBlocking'},
                       {'operation': 'Float_to_fixed', 'input_exponent': 4, 'output_exponent': 64, 'output_fraction': 0}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                plugin.validate_case(replace(case, parameters={**case.parameters, **change}))

    def test_absolute_clock_port_in_supported_versions(self):
        _, case = plugin_case('floating_point')
        for version, expected_clock in (("2026.1", "aclk"), ("2026.1.1", "aclk")):
            with self.subTest(version=version):
                plugin = FloatingPointPlugin(RepositoryLayout(ROOT, vivado_version=version),
                                             create_default_strategy_registry())
                spec = plugin.describe(case.parameters)
                self.assertEqual(spec.input_clock, expected_clock)
                self.assertIsNone(spec.input_reset)
                self.assertEqual("aclk" in {port.name for port in spec.inputs}, bool(expected_clock))

    def test_generation_is_reproducible_and_validates_exception_port_width(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, _ = plugin_case('floating_point', Path(directory))
            case = next(c for c in load_test_cases(ROOT / 'configs/ip/floating_point/regression.json')
                        if c.case_id == 'fp_f32_to_s17q9')
            spec = plugin.describe(case.parameters)
            self.assertEqual({port.name: port.width for port in spec.sink_payload}, {'tdata': 24, 'tlast': 1, 'tuser': 5})
            xci = Path(directory) / 'fixture.xci'
            xci.write_text('{}')
            with patch('vivado_ip_test.plugins.common.stream.testbench.load_metadata', return_value=(xci, {})):
                first = plugin.generate_testbench(case)
                contents = first.expected_path.read_bytes()
                second = plugin.generate_testbench(case)
            self.assertEqual(contents, second.expected_path.read_bytes())
            self.assertGreater(first.metrics['prepared_additional_transfers'], 0)
            self.assertEqual(first.metrics['reference_contract']['arithmetic'], 'integer_exact')

import unittest
from pathlib import Path
from vivado_ip_test.domain import Stage, Status, TestCase, VerificationProfile
from vivado_ip_test.infrastructure import RepositoryLayout
from vivado_ip_test.plugins import PluginError
from vivado_ip_test.plugins.divider import DividerPlugin
from vivado_ip_test.strategies import create_default_strategy_registry


def make_case(parameters):
    return TestCase(
        case_id="divider_case",
        ip_type="divider",
        vendor="xilinx.com",
        ip_name="div_gen",
        parameters=parameters,
        stages=(Stage.CREATE_IP,),
        verification=VerificationProfile(
            strategy="directed_random",
            strategy_version="1.0",
            random_seed=1,
            case_budget=16,
            coverage_targets=("boundary_values",),
        ),
    )


class DividerPluginTests(unittest.TestCase):
    def setUp(self):
        self.plugin = DividerPlugin(
            RepositoryLayout(Path("/tmp/repo")),
            create_default_strategy_registry(),
        )

    def test_accepts_supported_parameters(self):
        self.plugin.validate_case(
            make_case(
                {
                    "dividend_width": 16,
                    "divisor_width": 8,
                    "operand_sign": "Unsigned",
                }
            )
        )

    def test_rejects_invalid_width(self):
        with self.assertRaisesRegex(PluginError, "正整数"):
            self.plugin.validate_case(
                make_case(
                    {
                        "dividend_width": 0,
                        "divisor_width": 8,
                        "operand_sign": "Unsigned",
                    }
                )
            )

    def test_rejects_unknown_parameters(self):
        with self.assertRaisesRegex(PluginError, "未知 Divider 参数"):
            self.plugin.validate_case(
                make_case(
                    {
                        "dividend_width": 16,
                        "divisor_width": 8,
                        "operand_sign": "Unsigned",
                        "unexpected": True,
                    }
                )
            )

    def test_describes_demo_simulation_without_running_it(self):
        request = self.plugin.simulation_request(
            make_case(
                {
                    "dividend_width": 16,
                    "divisor_width": 8,
                    "operand_sign": "Unsigned",
                }
            ),
            Stage.SIM_DEMO,
        )

        self.assertEqual(request.top_name, "tb_div_gen_0")
        self.assertEqual(request.success_marker, "Test completed successfully")
        self.assertEqual(request.failure_status, Status.LOG_CHECK_FAILED)
        self.assertTrue(str(request.testbench_path).endswith("tb_div_gen_0.vhd"))

    def test_describes_selfcheck_simulation(self):
        request = self.plugin.simulation_request(
            make_case(
                {
                    "dividend_width": 16,
                    "divisor_width": 8,
                    "operand_sign": "Unsigned",
                }
            ),
            Stage.SIM_SELFCHECK,
        )

        self.assertEqual(request.top_name, "tb_divider_selfcheck")
        self.assertEqual(request.failure_status, Status.SIMULATION_FAILED)
        self.assertEqual(
            request.failure_markers,
            ("DIVIDER_SELF_CHECK_STATUS: FAIL",),
        )

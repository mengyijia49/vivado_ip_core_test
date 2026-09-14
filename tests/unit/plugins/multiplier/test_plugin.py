import unittest
from pathlib import Path

from vivado_ip_test.domain import Stage, Status, TestCase, VerificationProfile
from vivado_ip_test.infrastructure import RepositoryLayout
from vivado_ip_test.plugins import PluginError
from vivado_ip_test.plugins.multiplier import MultiplierPlugin
from vivado_ip_test.strategies import create_default_strategy_registry


def make_case(parameters, stages=(Stage.CREATE_IP,)):
    return TestCase(
        case_id="multiplier_case",
        ip_type="multiplier",
        vendor="xilinx.com",
        ip_name="mult_gen",
        parameters=parameters,
        stages=stages,
        verification=VerificationProfile(
            strategy="directed_random",
            strategy_version="1.0",
            random_seed=1,
            case_budget=16,
            coverage_targets=("boundary_values",),
        ),
    )


def valid_parameters():
    return {
        "a_width": 16,
        "b_width": 8,
        "a_type": "Signed",
        "b_type": "Unsigned",
        "pipeline_stages": 3,
    }


class MultiplierPluginTests(unittest.TestCase):
    def setUp(self):
        self.plugin = MultiplierPlugin(
            RepositoryLayout(Path("/tmp/repo")),
            create_default_strategy_registry(),
        )

    def test_accepts_supported_parameters(self):
        self.plugin.validate_case(make_case(valid_parameters()))

    def test_rejects_demo_stage_because_catalog_has_no_demo_testbench(self):
        with self.assertRaisesRegex(PluginError, "不提供官方 demo"):
            self.plugin.validate_case(
                make_case(valid_parameters(), (Stage.CREATE_IP, Stage.SIM_DEMO))
            )

    def test_rejects_invalid_operand_type(self):
        parameters = valid_parameters()
        parameters["a_type"] = "Invalid"
        with self.assertRaisesRegex(PluginError, "Unsigned 或 Signed"):
            self.plugin.validate_case(make_case(parameters))

    def test_build_request_uses_multiplier_tcl(self):
        request = self.plugin.build_request(make_case(valid_parameters()))

        self.assertEqual(request.source_path.parts[-3:], ("ip", "multiplier", "create_ip.tcl"))
        self.assertEqual(request.artifact_glob, "**/mult_gen_0.xci")

    def test_describes_selfcheck_simulation(self):
        request = self.plugin.simulation_request(
            make_case(valid_parameters()), Stage.SIM_SELFCHECK
        )

        self.assertEqual(request.top_name, "tb_multiplier_selfcheck")
        self.assertEqual(request.failure_status, Status.SIMULATION_FAILED)

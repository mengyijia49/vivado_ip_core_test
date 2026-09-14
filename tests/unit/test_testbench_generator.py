import tempfile
import unittest
from pathlib import Path

from vivado_ip_test.domain import (
    Stage,
    Status,
    TestCase,
    TestbenchArtifacts,
    VerificationProfile,
)
from vivado_ip_test.infrastructure import RepositoryLayout
from vivado_ip_test.plugins import PluginRegistry
from vivado_ip_test.services import TestbenchGenerator


class FakeGeneratorPlugin:
    ip_type = "fake"

    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.generated_case_id = None

    def generate_testbench(self, case):
        self.generated_case_id = case.case_id
        if self.should_fail:
            raise ValueError("intentional generation failure")
        base = Path("/tmp") / case.case_id
        return TestbenchArtifacts(
            testbench_path=base / "tb.vhd",
            input_path=base / "input.txt",
            expected_path=base / "expected.txt",
            actual_path=base / "actual.txt",
            manifest_path=base / "manifest.json",
            vector_count=7,
        )


def make_case():
    return TestCase(
        case_id="case_without_type_in_name",
        ip_type="fake",
        vendor="example.com",
        ip_name="example",
        parameters={},
        stages=(Stage.CREATE_IP, Stage.GENERATE_TESTBENCH),
        verification=VerificationProfile(
            strategy="directed_random",
            strategy_version="1.0",
            random_seed=1,
            case_budget=1,
            coverage_targets=("boundary_values",),
        ),
    )


class TestbenchGeneratorTests(unittest.TestCase):
    def build(self, temp_dir, plugin):
        registry = PluginRegistry()
        registry.register(plugin)
        layout = RepositoryLayout(Path(temp_dir))
        return TestbenchGenerator(registry, layout)

    def test_dispatches_through_the_registered_ip_plugin(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            plugin = FakeGeneratorPlugin()
            generator = self.build(temp_dir, plugin)

            result = generator.generate(make_case())

            self.assertEqual(result.status, Status.PASS)
            self.assertEqual(plugin.generated_case_id, "case_without_type_in_name")
            self.assertIn("STATUS: PASS", result.log_path.read_text())

    def test_classifies_backend_generation_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = self.build(temp_dir, FakeGeneratorPlugin(should_fail=True))

            result = generator.generate(make_case())

            self.assertEqual(result.status, Status.TESTBENCH_GENERATION_FAILED)
            self.assertIn("STATUS: FAIL", result.log_path.read_text())

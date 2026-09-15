import tempfile
from dataclasses import replace
import unittest
from pathlib import Path

from vivado_ip_test.domain import (
    BuildRequest,
    Stage,
    Status,
    TestCase as DomainTestCase,
    VerificationProfile,
)
from vivado_ip_test.infrastructure import CommandResult, RepositoryLayout
from vivado_ip_test.plugins import PluginRegistry
from vivado_ip_test.services import IpBuilder


class FakePlugin:
    ip_type = "fake_ip"

    def __init__(self, layout):
        self.layout = layout

    def build_request(self, case):
        return BuildRequest(
            description="Running fake build:",
            source_path=self.layout.root / "create.tcl",
            tclargs=(str(self.layout.case_run_dir(case)), "8"),
            log_path=self.layout.log_dir / "fake_create.log",
            journal_path=self.layout.log_dir / "fake_create.jou",
            success_marker="FAKE_BUILD_STATUS: PASS",
            artifact_glob="**/fake.xci",
        )


class FakeVivado:
    def __init__(self, result, log_text=None, create_artifact=False):
        self.result = result
        self.log_text = log_text
        self.create_artifact = create_artifact

    def run(self, **kwargs):
        if self.log_text is not None:
            kwargs["log_path"].write_text(self.log_text)
        if self.create_artifact:
            artifact = Path(kwargs["tclargs"][0]) / "proj" / "fake.xci"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text("{}")
        return self.result


def make_case():
    return DomainTestCase(
        case_id="fake_case",
        ip_type="fake_ip",
        vendor="example.com",
        ip_name="fake",
        parameters={},
        stages=(Stage.CREATE_IP,),
        verification=VerificationProfile(
            strategy="directed_random",
            strategy_version="1.0",
            random_seed=1,
            case_budget=1,
            coverage_targets=("boundary_values",),
        ),
    )


class IpBuilderTests(unittest.TestCase):
    def build(self, root, vivado):
        layout = RepositoryLayout(root)
        registry = PluginRegistry()
        registry.register(FakePlugin(layout))
        return IpBuilder(registry, layout, vivado)

    def test_accepts_success_marker_and_generated_xci(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = self.build(
                Path(temp_dir),
                FakeVivado(
                    CommandResult(0, ""),
                    "FAKE_BUILD_STATUS: PASS\n",
                    create_artifact=True,
                ),
            )

            result = builder.build(make_case())

            self.assertEqual(result.status, Status.PASS)

    def test_classifies_missing_success_marker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = self.build(
                Path(temp_dir),
                FakeVivado(CommandResult(0, ""), "unrelated log\n", True),
            )

            result = builder.build(make_case())

            self.assertEqual(result.status, Status.LOG_CHECK_FAILED)

    def test_classifies_missing_xci(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = self.build(
                Path(temp_dir),
                FakeVivado(CommandResult(0, ""), "FAKE_BUILD_STATUS: PASS\n"),
            )

            result = builder.build(make_case())

            self.assertEqual(result.status, Status.XCI_NOT_FOUND)

    def test_uses_explicit_block_design_artifact_and_missing_status(self):
        class InlinePlugin(FakePlugin):
            def build_request(self, case):
                return replace(super().build_request(case), artifact_glob="**/dut_0.bd",
                               missing_artifact_status=Status.BLOCK_DESIGN_NOT_FOUND)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            layout = RepositoryLayout(root)
            registry = PluginRegistry()
            registry.register(InlinePlugin(layout))
            builder = IpBuilder(registry, layout, FakeVivado(CommandResult(0, ""), "FAKE_BUILD_STATUS: PASS\n", True))
            self.assertEqual(builder.build(make_case()).status, Status.BLOCK_DESIGN_NOT_FOUND)
            bd = layout.case_run_dir(make_case()) / "proj/dut_0.bd"
            bd.write_text("{}")
            self.assertEqual(builder.build(make_case()).status, Status.PASS)

    def test_classifies_vivado_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            builder = self.build(Path(temp_dir), FakeVivado(CommandResult(1, "")))

            result = builder.build(make_case())

            self.assertEqual(result.status, Status.CREATE_IP_FAILED)

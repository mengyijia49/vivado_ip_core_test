from collections.abc import Iterable
from pathlib import Path

from vivado_ip_test.domain import Stage, StageResult, TestCase
from vivado_ip_test.plugins import PluginRegistry
from vivado_ip_test.services import (
    IpBuilder,
    ReportGenerator,
    RunRecorder,
    SimulationRunner,
    TestbenchGenerator,
)
from vivado_ip_test.strategies import StrategyRegistry


class AutomationPipeline:
    def __init__(
        self,
        registry: PluginRegistry,
        report_generator: ReportGenerator,
        testbench_generator: TestbenchGenerator,
        simulation_runner: SimulationRunner,
        ip_builder: IpBuilder,
        strategy_registry: StrategyRegistry,
    ) -> None:
        self._registry = registry
        self._report_generator = report_generator
        self._testbench_generator = testbench_generator
        self._simulation_runner = simulation_runner
        self._ip_builder = ip_builder
        self._strategy_registry = strategy_registry

    def validate(self, cases: Iterable[TestCase]) -> None:
        for case in cases:
            self._strategy_registry.resolve(case.verification)
            self._registry.resolve(case.ip_type).validate_case(case)

    def run(
        self,
        cases: Iterable[TestCase],
        report_path: Path,
        recorder: RunRecorder | None = None,
    ) -> list[StageResult]:
        results: list[StageResult] = []
        if recorder is None:
            self._write_reports(report_path, results)

        for case in cases:
            for stage in case.stages:
                if stage is Stage.CREATE_IP:
                    result = self._ip_builder.build(case)
                elif stage is Stage.GENERATE_TESTBENCH:
                    result = self._testbench_generator.generate(case)
                elif stage in {Stage.SIM_DEMO, Stage.SIM_SELFCHECK}:
                    result = self._simulation_runner.run(case, stage)
                else:
                    raise ValueError(f"流水线不支持阶段：{stage.value}")
                results.append(result)
                if recorder is not None:
                    recorder.capture(result)
                else:
                    self._write_reports(report_path, results)
                if not result.passed:
                    break

        return results

    def _write_reports(self, report_path: Path, results: list[StageResult]) -> None:
        self._report_generator.write_bundle(report_path, results)

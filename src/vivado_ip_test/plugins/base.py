from typing import Protocol

from vivado_ip_test.domain import (
    BuildRequest,
    SimulationRequest,
    Stage,
    Status,
    TestCase,
    TestbenchArtifacts,
)


class PluginError(ValueError):
    pass


class IpPlugin(Protocol):
    ip_type: str

    def validate_case(self, case: TestCase) -> None:
        ...

    def build_request(self, case: TestCase) -> BuildRequest:
        ...

    def generate_testbench(self, case: TestCase) -> TestbenchArtifacts:
        ...

    def simulation_request(
        self, case: TestCase, stage: Stage
    ) -> SimulationRequest:
        ...

    def verify_simulation(self, case: TestCase, stage: Stage) -> Status:
        ...

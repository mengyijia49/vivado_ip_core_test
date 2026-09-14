import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Mapping


class Stage(str, Enum):
    CREATE_IP = "create_ip"
    SIM_DEMO = "sim_demo"
    GENERATE_TESTBENCH = "generate_testbench"
    SIM_SELFCHECK = "sim_selfcheck"


class Status(str, Enum):
    VIVADO_NOT_FOUND = "VIVADO_NOT_FOUND"
    CREATE_IP_FAILED = "CREATE_IP_FAILED"
    TIMEOUT = "TIMEOUT"
    LOG_NOT_FOUND = "LOG_NOT_FOUND"
    LOG_CHECK_FAILED = "LOG_CHECK_FAILED"
    XCI_NOT_FOUND = "XCI_NOT_FOUND"
    TESTBENCH_GENERATION_FAILED = "TESTBENCH_GENERATION_FAILED"
    SIMULATION_FAILED = "SIMULATION_FAILED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    PASS = "PASS"


@dataclass(frozen=True)
class TestCase:
    case_id: str
    ip_type: str
    vendor: str
    ip_name: str
    parameters: Mapping[str, object]
    stages: tuple[Stage, ...]
    verification: "VerificationProfile"


@dataclass(frozen=True)
class VerificationProfile:
    strategy: str
    strategy_version: str
    random_seed: int
    case_budget: int
    coverage_targets: tuple[str, ...]
    boundary_mode: str = "basic"
    timing_mode: str = "continuous"
    max_gap_cycles: int = 8
    burst_length: int = 16
    input_order: str = "generated"

    def as_dict(self) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "strategy_version": self.strategy_version,
            "random_seed": self.random_seed,
            "case_budget": self.case_budget,
            "coverage_targets": list(self.coverage_targets),
            "boundary_mode": self.boundary_mode,
            "timing_mode": self.timing_mode,
            "max_gap_cycles": self.max_gap_cycles,
            "burst_length": self.burst_length,
            "input_order": self.input_order,
        }


@dataclass(frozen=True)
class TestbenchArtifacts:
    testbench_path: Path
    input_path: Path
    expected_path: Path
    actual_path: Path
    manifest_path: Path
    vector_count: int
    metrics: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class BuildRequest:
    description: str
    source_path: Path
    tclargs: tuple[str, ...]
    log_path: Path
    journal_path: Path
    success_marker: str
    artifact_glob: str


@dataclass(frozen=True)
class SimulationRequest:
    description: str
    project_path: Path
    testbench_path: Path
    top_name: str
    log_path: Path
    journal_path: Path
    success_marker: str
    failure_markers: tuple[str, ...]
    failure_status: Status


@dataclass(frozen=True)
class StageResult:
    case_id: str
    stage: Stage
    status: Status
    run_dir: Path
    log_path: Path
    ip_type: str = ""
    parameters: Mapping[str, object] = field(default_factory=dict)
    verification: VerificationProfile | None = None
    metrics: Mapping[str, object] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status is Status.PASS

    def as_csv_row(self) -> list[str]:
        return [
            self.case_id,
            self.stage.value,
            self.status.value,
            self.ip_type,
            json.dumps(
                dict(self.parameters),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            "" if self.verification is None else self.verification.strategy,
            "" if self.verification is None else self.verification.strategy_version,
            "" if self.verification is None else str(self.verification.random_seed),
            "" if self.verification is None else str(self.verification.case_budget),
            "" if self.verification is None else json.dumps(
                list(self.verification.coverage_targets),
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            json.dumps(
                dict(self.metrics),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            str(self.run_dir),
            str(self.log_path),
        ]

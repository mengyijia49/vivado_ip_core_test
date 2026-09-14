import random
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Generic, Hashable, Protocol, TypeVar

from vivado_ip_test.domain import VerificationProfile


CaseT = TypeVar("CaseT", bound=Hashable)


class StrategyError(ValueError):
    pass


@dataclass(frozen=True)
class CaseSpace(Generic[CaseT]):
    directed_cases: tuple[CaseT, ...]
    random_case: Callable[[random.Random], CaseT]
    exhaustive_cases: Callable[[], Iterable[CaseT]]
    total_case_count: int
    coverage_features: Callable[[CaseT], frozenset[str]]
    target_bins: dict[str, frozenset[str]] = field(default_factory=dict)


@dataclass(frozen=True)
class GenerationResult(Generic[CaseT]):
    cases: tuple[CaseT, ...]
    strategy: str
    strategy_version: str
    directed_count: int
    generated_count: int
    covered_targets: tuple[str, ...] = ()
    missing_targets: tuple[str, ...] = ()
    coverage_metrics: dict[str, object] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "strategy": self.strategy,
            "strategy_version": self.strategy_version,
            "directed_count": self.directed_count,
            "generated_count": self.generated_count,
            "covered_targets": list(self.covered_targets),
            "missing_targets": list(self.missing_targets),
            **self.coverage_metrics,
        }


class VectorGenerationStrategy(Protocol):
    name: str
    version: str

    def generate(
        self,
        space: CaseSpace[CaseT],
        profile: VerificationProfile,
    ) -> GenerationResult[CaseT]:
        ...

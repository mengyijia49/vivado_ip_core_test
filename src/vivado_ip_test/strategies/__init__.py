"""与 Vivado 执行解耦的测试用例生成策略。"""

from vivado_ip_test.strategies.base import (
    CaseSpace,
    GenerationResult,
    StrategyError,
    VectorGenerationStrategy,
)
from vivado_ip_test.strategies.directed_random import DirectedRandomStrategy
from vivado_ip_test.strategies.exhaustive import ExhaustiveStrategy
from vivado_ip_test.strategies.coverage_guided import CoverageGuidedStrategy
from vivado_ip_test.strategies.registry import StrategyRegistry


def create_default_strategy_registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    registry.register(DirectedRandomStrategy())
    registry.register(ExhaustiveStrategy())
    registry.register(CoverageGuidedStrategy())
    return registry


__all__ = [
    "CaseSpace",
    "CoverageGuidedStrategy",
    "DirectedRandomStrategy",
    "ExhaustiveStrategy",
    "GenerationResult",
    "StrategyError",
    "StrategyRegistry",
    "VectorGenerationStrategy",
    "create_default_strategy_registry",
]

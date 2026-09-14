from vivado_ip_test.domain import VerificationProfile
from vivado_ip_test.strategies.base import (
    CaseSpace,
    GenerationResult,
    StrategyError,
    VectorGenerationStrategy,
)
from vivado_ip_test.strategies.coverage import measure_coverage


class StrategyRegistry:
    def __init__(self) -> None:
        self._strategies: dict[str, VectorGenerationStrategy] = {}

    def register(self, strategy: VectorGenerationStrategy) -> None:
        if strategy.name in self._strategies:
            raise StrategyError(f"测试生成策略重复注册：{strategy.name}")
        self._strategies[strategy.name] = strategy

    def generate(
        self,
        space: CaseSpace,
        profile: VerificationProfile,
    ) -> GenerationResult:
        strategy = self.resolve(profile)
        result = strategy.generate(space, profile)
        if result.generated_count > profile.case_budget:
            raise StrategyError("策略生成数量超过用例预算")
        return measure_coverage(space, result, profile.coverage_targets)

    def resolve(self, profile: VerificationProfile) -> VectorGenerationStrategy:
        try:
            strategy = self._strategies[profile.strategy]
        except KeyError as exc:
            raise StrategyError(f"不支持的测试生成策略：{profile.strategy}") from exc
        if strategy.version != profile.strategy_version:
            raise StrategyError(
                f"策略 {profile.strategy} 的版本不匹配："
                f"配置要求 {profile.strategy_version}，当前为 {strategy.version}"
            )
        return strategy

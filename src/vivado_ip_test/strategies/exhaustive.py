from vivado_ip_test.strategies.base import GenerationResult, StrategyError


class ExhaustiveStrategy:
    name = "exhaustive"
    version = "1.0"

    def generate(self, space, profile):
        if profile.case_budget < space.total_case_count:
            raise StrategyError(
                f"穷举策略需要至少 {space.total_case_count} 个用例预算，"
                f"当前为 {profile.case_budget}"
            )
        cases = tuple(dict.fromkeys(space.exhaustive_cases()))
        if len(cases) != space.total_case_count:
            raise StrategyError(
                "输入空间声明数量与穷举生成数量不一致："
                f"{space.total_case_count} != {len(cases)}"
            )
        directed = set(space.directed_cases)
        return GenerationResult(
            cases=cases,
            strategy=self.name,
            strategy_version=self.version,
            directed_count=sum(case in directed for case in cases),
            generated_count=len(cases),
            covered_targets=tuple(),
            missing_targets=tuple(),
        )

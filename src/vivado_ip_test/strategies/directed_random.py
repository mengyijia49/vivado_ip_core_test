import random
from vivado_ip_test.domain.counts import count_for_report

from vivado_ip_test.strategies.base import (
    CaseSpace,
    GenerationResult,
    StrategyError,
)

class DirectedRandomStrategy:
    name = "directed_random"
    version = "1.0"

    def generate(self, space, profile):
        cases = list(dict.fromkeys(space.directed_cases))
        if profile.case_budget < len(cases):
            raise StrategyError(
                f"用例预算 {profile.case_budget} 小于定向用例数 {len(cases)}"
            )
        if profile.case_budget > space.total_case_count:
            raise StrategyError(
                f"用例预算 {profile.case_budget} 超过输入空间大小 "
                f"{count_for_report(space.total_case_count)}"
            )

        seen = set(cases)
        generator = random.Random(profile.random_seed)
        attempts = 0
        attempt_limit = max(1000, profile.case_budget * 100)
        while len(cases) < profile.case_budget and attempts < attempt_limit:
            candidate = space.random_case(generator)
            attempts += 1
            if candidate not in seen:
                cases.append(candidate)
                seen.add(candidate)

        if len(cases) < profile.case_budget:
            for candidate in space.exhaustive_cases():
                if candidate not in seen:
                    cases.append(candidate)
                    seen.add(candidate)
                    if len(cases) == profile.case_budget:
                        break

        if len(cases) != profile.case_budget:
            raise StrategyError("无法在指定预算内生成足够的唯一测试用例")

        return GenerationResult(
            cases=tuple(cases),
            strategy=self.name,
            strategy_version=self.version,
            directed_count=len(tuple(dict.fromkeys(space.directed_cases))),
            generated_count=len(cases),
            covered_targets=tuple(),
            missing_targets=tuple(),
        )

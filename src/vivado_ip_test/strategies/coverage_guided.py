import random

from vivado_ip_test.strategies.base import GenerationResult, StrategyError


class CoverageGuidedStrategy:
    """使用贪心覆盖增益选择输入，保持固定种子下的确定性。"""

    name = "coverage_guided"
    version = "1.0"

    def generate(self, space, profile):
        directed = list(dict.fromkeys(space.directed_cases))
        if profile.case_budget < len(directed):
            raise StrategyError(
                f"用例预算 {profile.case_budget} 小于定向用例数 {len(directed)}"
            )
        if profile.case_budget > space.total_case_count:
            raise StrategyError(
                f"用例预算 {profile.case_budget} 超过输入空间大小 "
                f"{space.total_case_count}"
            )

        targets = set()
        for target in profile.coverage_targets:
            if target != "complete_input_space":
                targets.update(space.target_bins.get(target, {target}))
        cases = list(directed)
        seen = set(cases)
        covered = set().union(*(space.coverage_features(case) for case in cases))
        generator = random.Random(profile.random_seed)
        candidates = []
        candidate_seen = set()
        pool_size = max(1000, profile.case_budget * 64)
        for _ in range(pool_size):
            candidate = space.random_case(generator)
            if candidate not in seen and candidate not in candidate_seen:
                candidates.append(candidate)
                candidate_seen.add(candidate)

        while len(cases) < profile.case_budget:
            best = None
            best_score = None
            for candidate_index, candidate in enumerate(candidates):
                features = space.coverage_features(candidate)
                score = (
                    len((features & targets) - covered),
                    len(features - covered),
                    -candidate_index,
                )
                if best_score is None or score > best_score:
                    best = candidate
                    best_score = score
            if best is None:
                for candidate in space.exhaustive_cases():
                    if candidate not in seen:
                        best = candidate
                        break
            if best is None:
                raise StrategyError("覆盖引导策略无法生成足够的唯一测试用例")
            cases.append(best)
            seen.add(best)
            candidates = [candidate for candidate in candidates if candidate != best]
            covered.update(space.coverage_features(best))

        return GenerationResult(
            cases=tuple(cases),
            strategy=self.name,
            strategy_version=self.version,
            directed_count=len(directed),
            generated_count=len(cases),
        )

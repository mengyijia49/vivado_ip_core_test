from dataclasses import replace

from vivado_ip_test.strategies.base import CaseSpace, GenerationResult, StrategyError


def measure_coverage(space: CaseSpace, result: GenerationResult, targets):
    """以同一套输入分箱统计所有策略，完整空间按唯一输入数量计数。"""
    unique_count = len(set(result.cases))
    if unique_count != len(result.cases) or result.generated_count != unique_count:
        raise StrategyError("策略生成数量不一致或包含重复输入")
    if not 0 < unique_count <= space.total_case_count:
        raise StrategyError("策略生成数量不在输入空间范围内")
    observed = set()
    for case in result.cases:
        observed.update(space.coverage_features(case))

    covered = []
    missing = []
    target_results = {}
    for target in sorted(targets):
        if target == "complete_input_space":
            hit_count, total_count = unique_count, space.total_case_count
            detail = {}
        else:
            bins = space.target_bins.get(target, frozenset({target}))
            if not bins:
                raise StrategyError(f"覆盖目标没有可达分箱：{target}")
            hit = bins & observed
            hit_count, total_count = len(hit), len(bins)
            detail = {"hit_bins": sorted(hit), "missing_bins": sorted(bins - hit)}
        target_results[target] = {
            **detail,
            "hit_count": hit_count,
            "total_count": total_count,
            "fraction": hit_count / total_count,
        }
        (covered if hit_count == total_count else missing).append(target)

    return replace(
        result,
        covered_targets=tuple(covered),
        missing_targets=tuple(missing),
        coverage_metrics={
            "coverage_model": "input_bins:1.0",
            "unique_count": unique_count,
            "input_space_size": space.total_case_count,
            "input_space_fraction": unique_count / space.total_case_count,
            "target_coverage": target_results,
        },
    )

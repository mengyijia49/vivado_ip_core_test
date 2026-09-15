"""完整检查输入流，只保留本次需要执行的配置。"""

from dataclasses import replace

from vivado_ip_test.configuration import ConfigError


def select_cases(cases, *, validate, ip_types=None, case_ids=None, seed=None,
                 budget=None, limit=None, completed=None):
    requested_ips, requested_ids = set(ip_types or ()), set(case_ids or ())
    available_ips, found_ids = set(), set()
    selected, skipped = [], 0
    completed = completed or {}
    for case in cases:
        available_ips.add(case.ip_type)
        if requested_ips and case.ip_type not in requested_ips:
            continue
        if seed is not None and "__seed" in case.case_id:
            raise ConfigError("探索矩阵请直接修改 exploration.seeds，不能再用 --seed 覆盖")
        if requested_ids:
            if case.case_id not in requested_ids:
                continue
            found_ids.add(case.case_id)
        if seed is not None or budget is not None:
            case = replace(case, verification=replace(case.verification,
                random_seed=case.verification.random_seed if seed is None else seed,
                case_budget=case.verification.case_budget if budget is None else budget))
        validate((case,))
        if case in completed.get(case.case_id, ()):
            skipped += 1
        elif limit is None or len(selected) < limit:
            selected.append(case)
    unknown = requested_ips - available_ips
    if unknown:
        raise ConfigError(f"配置中不存在 IP 类型：{', '.join(sorted(unknown))}")
    unknown = requested_ids - found_ids
    if unknown:
        raise ConfigError(f"配置中不存在用例：{', '.join(sorted(unknown))}")
    return selected, skipped

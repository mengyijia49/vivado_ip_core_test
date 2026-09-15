from copy import deepcopy
from itertools import product
from math import prod
import json
import re


MAX_SWEEP_CASES = 20000


def axis_option(raw):
    if type(raw) in (int, str, bool):
        return (str(raw).lower() if isinstance(raw, bool) else str(raw)), raw
    if not isinstance(raw, dict) or set(raw) != {"label", "value"}:
        raise ValueError("参数轴选项须为标量或 label/value 对象")
    label, value = raw["label"], raw["value"]
    if not isinstance(label, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", label):
        raise ValueError("参数轴 label 必须是合法标识符")
    if type(value) not in (int, str, bool) and not (
            isinstance(value, list) and value and all(type(v) in (int, str, bool) for v in value)):
        raise ValueError("命名参数值只支持标量或非空标量数组")
    return label, value


def expand_sweeps(sweeps):
    return list(iter_sweep_cases(sweeps))


def iter_sweep_cases(sweeps):
    if not isinstance(sweeps, list) or not sweeps:
        raise ValueError("sweeps 必须是非空数组")
    count = 0
    for sweep in sweeps:
        if not isinstance(sweep, dict) or set(sweep) != {"case_prefix", "template", "axes"}:
            raise ValueError("每个 sweep 必须且只能包含 case_prefix、template、axes")
        prefix, template, axes = sweep["case_prefix"], sweep["template"], sweep["axes"]
        if not isinstance(prefix, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", prefix):
            raise ValueError("case_prefix 必须是合法标识符")
        if not isinstance(template, dict) or "case_id" in template or not isinstance(template.get("parameters"), dict):
            raise ValueError("template 需要 parameters，不能包含 case_id")
        if not isinstance(axes, dict) or not axes or set(axes) - set(template["parameters"]):
            raise ValueError("axes 必须引用 template.parameters 中的参数")
        options = {}
        for name, values in axes.items():
            if not isinstance(values, list) or not values:
                raise ValueError("参数轴必须是非空数组")
            parsed = [axis_option(value) for value in values]
            if len({json.dumps(value, sort_keys=True) for _, value in parsed}) != len(values):
                raise ValueError("参数轴包含重复值")
            if len({label for label, _ in parsed}) != len(values):
                raise ValueError("参数轴包含重复 label")
            options[name] = parsed
        count += prod(len(values) for values in axes.values())
        if count > MAX_SWEEP_CASES:
            raise ValueError(f"单个配置文件最多展开 {MAX_SWEEP_CASES} 个参数配置")
        # 标量值或显式名称进入 ID；完整参数值仍保存在展开后的配置中。
        for values in product(*options.values()):
            case = deepcopy(template)
            suffix = "__".join(f"{name}_{label}" for name, (label, _) in zip(axes, values))
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", suffix):
                raise ValueError("参数轴的值不能用于 case_id")
            case["case_id"] = f"{prefix}__{suffix}"
            if len(case["case_id"].encode()) > 180:
                raise ValueError("展开后的 case_id 过长，请缩短前缀或拆分参数轴")
            case["parameters"].update((name, deepcopy(value)) for name, (_, value) in zip(axes, values))
            yield case

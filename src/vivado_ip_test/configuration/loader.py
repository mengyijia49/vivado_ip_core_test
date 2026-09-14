import json
import re
from dataclasses import replace
from pathlib import Path

from vivado_ip_test.domain import Stage, TestCase, VerificationProfile


class ConfigError(ValueError):
    pass


_CASE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_REQUIRED_CASE_FIELDS = {
    "case_id",
    "ip_type",
    "vendor",
    "ip_name",
    "parameters",
    "stages",
    "verification",
}
_ALLOWED_TOP_LEVEL_FIELDS = {"$schema", "schema_version", "cases", "exploration", "includes"}
_TIMING_MODES = {"continuous", "random_gaps", "bursts"}


def _require_nonempty_string(value: object, field: str, index: int) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigError(f"cases[{index}].{field} 必须是非空字符串")
    return value


def _parse_case(raw_case: object, index: int) -> TestCase:
    if not isinstance(raw_case, dict):
        raise ConfigError(f"cases[{index}] 必须是对象")

    missing = _REQUIRED_CASE_FIELDS - raw_case.keys()
    if missing:
        names = ", ".join(sorted(missing))
        raise ConfigError(f"cases[{index}] 缺少字段：{names}")
    unknown = raw_case.keys() - _REQUIRED_CASE_FIELDS
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ConfigError(f"cases[{index}] 包含未知字段：{names}")

    case_id = _require_nonempty_string(raw_case["case_id"], "case_id", index)
    if not _CASE_ID_PATTERN.fullmatch(case_id):
        raise ConfigError(f"cases[{index}].case_id 包含非法字符：{case_id}")

    parameters = raw_case["parameters"]
    if not isinstance(parameters, dict):
        raise ConfigError(f"cases[{index}].parameters 必须是对象")

    raw_stages = raw_case["stages"]
    if not isinstance(raw_stages, list) or not raw_stages:
        raise ConfigError(f"cases[{index}].stages 必须是非空数组")

    try:
        stages = tuple(Stage(item) for item in raw_stages)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"cases[{index}].stages 包含不支持的阶段") from exc

    if len(set(stages)) != len(stages):
        raise ConfigError(f"cases[{index}].stages 不允许重复")
    if stages[0] is not Stage.CREATE_IP:
        raise ConfigError(f"cases[{index}].stages 必须以 create_ip 开始")
    if Stage.SIM_SELFCHECK in stages:
        simulation_index = stages.index(Stage.SIM_SELFCHECK)
        if Stage.GENERATE_TESTBENCH not in stages[:simulation_index]:
            raise ConfigError(
                f"cases[{index}] 必须在 sim_selfcheck 前执行 generate_testbench"
            )

    raw_verification = raw_case["verification"]
    if not isinstance(raw_verification, dict):
        raise ConfigError(f"cases[{index}].verification 必须是对象")
    verification_fields = {
        "strategy",
        "strategy_version",
        "random_seed",
        "case_budget",
        "coverage_targets",
    }
    optional_fields = {"boundary_mode", "timing_mode", "max_gap_cycles", "burst_length", "input_order"}
    if (verification_fields - raw_verification.keys()
            or raw_verification.keys() - verification_fields - optional_fields):
        raise ConfigError(
            f"cases[{index}].verification 缺少必填字段或包含未知字段，必填："
            f"{', '.join(sorted(verification_fields))}"
        )
    strategy = _require_nonempty_string(
        raw_verification["strategy"], "verification.strategy", index
    )
    strategy_version = _require_nonempty_string(
        raw_verification["strategy_version"],
        "verification.strategy_version",
        index,
    )
    random_seed = raw_verification["random_seed"]
    case_budget = raw_verification["case_budget"]
    if type(random_seed) is not int or random_seed < 0:
        raise ConfigError(f"cases[{index}].verification.random_seed 必须是非负整数")
    if type(case_budget) is not int or case_budget <= 0:
        raise ConfigError(f"cases[{index}].verification.case_budget 必须是正整数")
    coverage_targets = raw_verification["coverage_targets"]
    if (
        not isinstance(coverage_targets, list)
        or not coverage_targets
        or any(not isinstance(item, str) or not item for item in coverage_targets)
        or len(set(coverage_targets)) != len(coverage_targets)
    ):
        raise ConfigError(
            f"cases[{index}].verification.coverage_targets "
            "必须是非空且不重复的字符串数组"
        )

    boundary_mode = raw_verification.get("boundary_mode", "basic")
    timing_mode = raw_verification.get("timing_mode", "continuous")
    input_order = raw_verification.get("input_order", "generated")
    if input_order not in ("generated", "shuffled"):
        raise ConfigError("input_order 必须是 generated 或 shuffled")
    if boundary_mode not in ("basic", "systematic"):
        raise ConfigError("boundary_mode 必须是 basic 或 systematic")
    if timing_mode not in tuple(_TIMING_MODES):
        raise ConfigError("不支持的 timing_mode")
    max_gap = raw_verification.get("max_gap_cycles", 8)
    burst_length = raw_verification.get("burst_length", 16)
    for name, value in (("max_gap_cycles", max_gap), ("burst_length", burst_length)):
        if type(value) is not int or not 1 <= value <= 10000:
            raise ConfigError(f"{name} 必须是 1 到 10000 的整数")

    ip_type = _require_nonempty_string(raw_case["ip_type"], "ip_type", index)
    if not _CASE_ID_PATTERN.fullmatch(ip_type):
        raise ConfigError("ip_type 必须是可用作目录名的标识符")
    return TestCase(
        case_id=case_id,
        ip_type=ip_type,
        vendor=_require_nonempty_string(raw_case["vendor"], "vendor", index),
        ip_name=_require_nonempty_string(raw_case["ip_name"], "ip_name", index),
        parameters=parameters,
        stages=stages,
        verification=VerificationProfile(
            strategy=strategy,
            strategy_version=strategy_version,
            random_seed=random_seed,
            case_budget=case_budget,
            coverage_targets=tuple(coverage_targets),
            boundary_mode=boundary_mode,
            timing_mode=timing_mode,
            max_gap_cycles=max_gap,
            burst_length=burst_length,
            input_order=input_order,
        ),
    )


def load_test_cases(path: Path) -> list[TestCase]:
    return _load_test_cases(path.resolve(), ())


def _load_test_cases(path: Path, ancestors: tuple[Path, ...]) -> list[TestCase]:
    if path in ancestors:
        raise ConfigError(f"配置 includes 存在循环引用：{path}")
    try:
        raw_config = json.loads(path.read_text())
    except OSError as exc:
        raise ConfigError(f"无法读取配置文件：{path}：{exc}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"配置文件不是有效 JSON：{exc}") from exc

    if not isinstance(raw_config, dict):
        raise ConfigError("配置文件顶层必须是对象")
    unknown = raw_config.keys() - _ALLOWED_TOP_LEVEL_FIELDS
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ConfigError(f"配置文件包含未知字段：{names}")
    if raw_config.get("schema_version") != 2:
        raise ConfigError("仅支持 schema_version = 2")

    if ("cases" in raw_config) == ("includes" in raw_config):
        raise ConfigError("配置必须且只能选择 cases 或 includes，公共入口只引用各 IP 配置")
    raw_cases = raw_config.get("cases", [])
    if not isinstance(raw_cases, list) or ("cases" in raw_config and not raw_cases):
        raise ConfigError("cases 必须是非空数组")

    cases = [_parse_case(raw_case, index) for index, raw_case in enumerate(raw_cases)]
    if len({case.ip_type for case in cases}) > 1:
        raise ConfigError("同一个配置文件不能混合不同 ip_type，请按 IP 拆分并使用 includes")
    if "includes" in raw_config:
        includes = raw_config["includes"]
        if (not isinstance(includes, list) or not includes
                or any(not isinstance(value, str) or not value for value in includes)):
            raise ConfigError("includes 必须是非空路径数组")
        for relative in includes:
            child = (path.parent / relative).resolve()
            cases.extend(_load_test_cases(child, (*ancestors, path)))
    case_ids = [case.case_id for case in cases]
    if len(set(case_ids)) != len(case_ids):
        raise ConfigError("case_id 必须唯一")

    if "exploration" not in raw_config:
        return cases
    if ancestors:
        raise ConfigError("exploration 只能放在本次加载的顶层入口，不能在 includes 中嵌套展开")
    exploration = raw_config["exploration"]
    if not isinstance(exploration, dict) or set(exploration) != {"seeds", "timing_modes"}:
        raise ConfigError("exploration 必须且只能包含 seeds 和 timing_modes")
    seeds = exploration["seeds"]
    modes = exploration["timing_modes"]
    if (not isinstance(seeds, list) or not seeds
            or any(type(seed) is not int or seed < 0 for seed in seeds)
            or len(set(seeds)) != len(seeds)):
        raise ConfigError("exploration.seeds 必须是非空且不重复的非负整数数组")
    if (not isinstance(modes, list) or not modes
            or any(not isinstance(mode, str) or mode not in _TIMING_MODES for mode in modes)
            or len(set(modes)) != len(modes)):
        raise ConfigError("exploration.timing_modes 包含非法或重复模式")
    expanded = [
        replace(case, case_id=f"{case.case_id}__seed{seed}__{mode}",
                verification=replace(case.verification, random_seed=seed, timing_mode=mode))
        for case in cases for seed in seeds for mode in modes
    ]
    if len({case.case_id for case in expanded}) != len(expanded):
        raise ConfigError("展开后的 case_id 必须唯一")
    return expanded

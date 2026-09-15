import argparse
import json
import sys
from contextlib import closing
from pathlib import Path

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.application.pipeline import AutomationPipeline
from vivado_ip_test.configuration import ConfigError, iter_test_cases
from vivado_ip_test.application.selection import select_cases
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout
from vivado_ip_test.infrastructure.workspace_lock import WorkspaceBusy, workspace_lock
from vivado_ip_test.plugins import PluginError
from vivado_ip_test.plugins.catalog import create_plugin_registry
from vivado_ip_test.services import (
    IpBuilder,
    ReportGenerator,
    RunRecorder,
    SimulationRunner,
    TestbenchGenerator,
)
from vivado_ip_test.strategies import StrategyError, create_default_strategy_registry
from vivado_ip_test.services.resume import load_completed_cases


def build_pipeline(layout: RepositoryLayout) -> AutomationPipeline:
    command_runner = CommandRunner()
    vivado = VivadoBatchRunner(command_runner, layout.root)
    strategy_registry = create_default_strategy_registry()
    registry = create_plugin_registry(layout, strategy_registry)
    return AutomationPipeline(
        registry,
        ReportGenerator(),
        TestbenchGenerator(registry, layout),
        SimulationRunner(registry, layout, vivado),
        IpBuilder(registry, layout, vivado),
        strategy_registry,
    )


def main(root: Path | None = None, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运行 Vivado IP 缺陷探索与数值自检")
    parser.add_argument("--config", type=Path, help="测试矩阵路径")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--ip-type", action="append", dest="ip_types",
                           help="只运行该类 IP，可重复指定；未指定配置时使用扩展回归")
    selection.add_argument("--all", action="store_true", help="运行全部 IP 的扩展回归；不自动运行大矩阵")
    parser.add_argument("--case", action="append", dest="case_ids", help="只运行指定用例，可重复指定")
    parser.add_argument("--seed", type=int, help="覆盖所选用例的随机种子")
    parser.add_argument("--budget", type=int, help="覆盖所选用例的向量预算")
    parser.add_argument("--workspace", type=Path, help="运行产物所在仓库，供归档源码复现使用")
    parser.add_argument("--list-cases", action="store_true", help="列出配置用例后退出")
    parser.add_argument("--limit", type=int, help="本次最多执行的配置数，适合分批探索")
    parser.add_argument("--resume-from", type=Path, action="append", default=[],
                        help="跳过指定历史 run.json 中完整通过且配置和源码一致的用例，可重复指定")
    args = parser.parse_args(argv)
    source_root = (root or Path.cwd()).resolve()
    layout = RepositoryLayout((args.workspace or source_root).resolve(), source_root)

    try:
        if args.seed is not None and args.seed < 0:
            raise ConfigError("随机种子必须为非负整数")
        if args.budget is not None and args.budget <= 0:
            raise ConfigError("用例预算必须为正整数")
        if args.limit is not None and args.limit <= 0:
            raise ConfigError("limit 必须为正整数")
        default_config = (source_root / "configs/extended_regression.json"
                          if args.all or args.ip_types else layout.config_path)
        pipeline = build_pipeline(layout)
        completed = load_completed_cases(layout, args.resume_from) if args.resume_from else {}
        with closing(iter_test_cases(args.config or default_config)) as candidates:
            cases, skipped = select_cases(candidates, validate=pipeline.validate,
                ip_types=args.ip_types, case_ids=args.case_ids, seed=args.seed, budget=args.budget,
                limit=args.limit, completed=completed)
        if args.resume_from:
            print(f"已核对归档证据，跳过 {skipped} 个完整通过的配置。")
    except (ConfigError, PluginError, StrategyError) as exc:
        print(f"配置错误：{exc}", file=sys.stderr)
        return 2

    if args.list_cases:
        for case in cases:
            profile = case.verification
            print(f"{case.case_id}\t{case.ip_type}\t{profile.strategy}"
                  f"\tseed={profile.random_seed}\tbudget={profile.case_budget}"
                  f"\t{profile.boundary_mode}\t{profile.timing_mode}"
                  f"\tparameters={json.dumps(dict(case.parameters), sort_keys=True)}")
        print(f"配置数={len(cases)}，阶段数={sum(len(case.stages) for case in cases)}，"
              f"向量预算合计={sum(case.verification.case_budget for case in cases)}")
        return 0

    if not cases:
        print("没有待执行配置；未改写最新报告。")
        return 0

    try:
        with workspace_lock(layout.runs_dir):
            with RunRecorder(layout, cases) as recorder:
                recorder.metadata["resumed_from"] = [str(path.resolve()) for path in args.resume_from]
                print(f"Run ID: {recorder.run_id}", flush=True)
                results = pipeline.run(cases, layout.report_path, recorder)
    except WorkspaceBusy as exc:
        print(str(exc), file=sys.stderr)
        return 3

    print("\nReports written to:")
    print(layout.report_path)
    print(layout.report_path.with_suffix(".json"))
    print(recorder.report_dir / "run.json")
    print("\nResult:")
    for result in results:
        print(",".join(result.as_csv_row()))

    return 0 if all(result.passed for result in results) else 1

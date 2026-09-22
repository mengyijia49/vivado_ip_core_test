"""以完整配置和归档证据匹配为条件跳过已完成配置，不复用中间工程状态。"""

import json
import re
from collections import defaultdict
from pathlib import Path

from vivado_ip_test.configuration import ConfigError, load_test_cases
from vivado_ip_test.infrastructure import RepositoryLayout, sha256_file
from vivado_ip_test.infrastructure.source_inventory import source_inventory


def remaining_cases(layout: RepositoryLayout, cases, records: list[Path]):
    completed = load_completed_cases(layout, records)
    return [case for case in cases if case not in completed.get(case.case_id, ())]


def _record_version(record):
    if record.get("vivado_version"):
        return record["vivado_version"]
    executable = record.get("vivado_executable") or ""
    match = re.search(r"/(\d{4}\.\d+(?:\.\d+)?)/Vivado/", executable)
    return match.group(1) if match else None


def load_completed_cases(layout: RepositoryLayout, records: list[Path]):
    completed = defaultdict(list)
    sources = source_inventory(layout.source_root or layout.root)
    for record_path in records:
        try:
            record = json.loads(record_path.read_text())
            if layout.vivado_version is not None and _record_version(record) != layout.vivado_version:
                raise ConfigError(f"续跑记录的 Vivado 版本不匹配：{record_path}")
            if record.get("source_sha256") != sources:
                raise ConfigError(f"续跑源码与归档不一致：{record_path}")
            version = record.get("vivado_version")
            archive = layout.runs_dir / "history"
            if version:
                archive = archive / version
            archive = archive / record["run_id"]
            config_path = archive / "ip_matrix.json"
            hashes = record["artifact_sha256"]
            config_key = str(config_path.relative_to(layout.root))
            if config_key not in hashes:
                raise ConfigError("续跑归档缺少配置哈希")
            for relative, digest in hashes.items():
                artifact = (layout.root / relative).resolve()
                if not artifact.is_relative_to(layout.root.resolve()) or sha256_file(artifact) != digest:
                    raise ConfigError(f"续跑证据哈希不匹配：{relative}")
            old_cases = load_test_cases(config_path)
            results = json.loads(record_path.with_name("report.json").read_text())
            observed_by_case = defaultdict(list)
            for result in results:
                observed_by_case[result["case_id"]].append((result["stage"], result["status"]))
            for case in old_cases:
                observed = observed_by_case[case.case_id]
                if observed == [(stage.value, "PASS") for stage in case.stages]:
                    completed[case.case_id].append(case)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise ConfigError(f"不能使用续跑记录 {record_path}：{exc}") from exc
    return dict(completed)

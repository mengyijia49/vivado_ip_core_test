"""一次性整理旧版产物；默认仅预览，移动前后核对内容，不改写工程或历史证据。"""

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from vivado_ip_test.infrastructure.hashing import sha256_file
from vivado_ip_test.infrastructure.run_identity import create_run_id
from vivado_ip_test.infrastructure.workspace_lock import workspace_lock


def content_digest(path: Path) -> str:
    digest = hashlib.sha256()
    entries = [path] if path.is_file() or path.is_symlink() else sorted(path.rglob("*"))
    for entry in entries:
        relative = "." if entry == path else str(entry.relative_to(path))
        if entry.is_symlink():
            content = f"link:{entry.readlink()}"
        elif entry.is_file():
            content = sha256_file(entry)
        else:
            content = "directory"
        digest.update(json.dumps([relative, content]).encode())
    return digest.hexdigest()


def migration_plan(root: Path, batch: str):
    runs, logs = root / "runs", root / "runs/logs"
    artifacts = runs / "legacy" / batch
    log_archive = logs / "legacy" / batch
    moves = []
    case_types = {}
    for path in sorted(runs.iterdir()):
        if not path.is_dir() or path.name in {"batches", "current", "history", "logs", "legacy", "framework", "work"}:
            continue
        manifest = path / "manifest.json"
        if manifest.is_file():
            ip_type = json.loads(manifest.read_text())["ip_type"]
            if ip_type not in {"divider", "multiplier"}:
                raise ValueError(f"需要人工归类的旧 IP：{path}")
            case_types[path.name] = ip_type
            moves.append((path, artifacts / "ip" / ip_type / path.name))
        elif path.name == "divider_default":
            case_types[path.name] = "divider"
            moves.append((path, artifacts / "ip/divider" / path.name))
        elif path.name in {"acceptance_missing_vivado", "acceptance_replay", "framework_checks",
                           "ip_catalog_check_proj", "replay_validation"}:
            moves.append((path, artifacts / "framework" / path.name))
        else:
            raise ValueError(f"不能自动归类旧目录：{path}")
    for path in sorted(logs.iterdir()):
        if path.is_file():
            case_id = next((name for name in sorted(case_types, key=len, reverse=True)
                            if path.name.startswith(name + "_")), None)
            target = log_archive / "ip" / case_types[case_id] / case_id if case_id else log_archive / "framework"
            moves.append((path, target / path.name))
        elif path.name == "framework_checks":
            moves.append((path, log_archive / "framework/failure_detection"))
    for path in sorted(runs.iterdir()):
        if path.is_file() and path.suffix in {".log", ".jou"}:
            moves.append((path, log_archive / "framework/imported" / path.name))
    for name in (".Xil", "xvlog.pb", "vivado.log", "vivado.jou"):
        path = root / name
        if path.exists():
            target = log_archive / "tool_work" if path.suffix in {".log", ".jou"} else artifacts / "tool_work"
            moves.append((path, target / name))
    for name in ("report.csv", "report.json"):
        path = root / "reports" / name
        if path.exists():
            moves.append((path, root / "reports/legacy" / batch / name))
    return moves


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="实际移动；默认只预览")
    args = parser.parse_args(argv)
    batch = create_run_id()
    with workspace_lock(ROOT / "runs"):
        moves = migration_plan(ROOT, batch)
        for source, target in moves:
            if target.exists():
                raise FileExistsError(target)
            print(f"{source.relative_to(ROOT)} -> {target.relative_to(ROOT)}")
        if not args.apply:
            return 0
        record_path = ROOT / "reports/maintenance" / batch / "layout_migration.json"
        record_path.parent.mkdir(parents=True, exist_ok=False)
        records = []
        for source, target in moves:
            digest = content_digest(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            source.rename(target)
            if content_digest(target) != digest:
                raise RuntimeError(f"迁移后内容不一致：{target}")
            records.append({"from": str(source.relative_to(ROOT)), "to": str(target.relative_to(ROOT)),
                            "content_sha256": digest})
            record_path.write_text(json.dumps(records, indent=2) + "\n")
        empty_tb = ROOT / "tb"
        if empty_tb.is_dir() and not any(empty_tb.iterdir()):
            empty_tb.rmdir()
        print(f"已核对并迁移 {len(records)} 个条目。清单：{record_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

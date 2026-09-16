"""Export selected local evidence, or verify the public copies without Vivado."""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 8 * 1024 * 1024
RUN_ID = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}_UTC[+-]\d{4}_[A-Za-z0-9]+$")
PRIVATE = re.compile(r"github_pat_[A-Za-z0-9_]+|gh[pousr]_[A-Za-z0-9]+|"
                     r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def beneath(root, relative):
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"Invalid relative path: {relative}")
    target = root / path
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes its root: {relative}")
    return target


def read_small(path):
    if path.stat().st_size > MAX_BYTES:
        raise ValueError(f"Evidence file exceeds {MAX_BYTES} bytes: {path}")
    data = path.read_bytes()
    text = data.decode("utf-8")
    if PRIVATE.search(text):
        raise ValueError(f"Credential pattern found in {path}")
    return data


def replace_paths(value, replacements):
    if isinstance(value, str):
        for old, new in replacements.items():
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [replace_paths(item, replacements) for item in value]
    if isinstance(value, dict):
        return {replace_paths(key, replacements): replace_paths(item, replacements)
                for key, item in value.items()}
    return value


def transform(data, entry, replacements):
    mode = entry["mode"]
    text = data.decode("utf-8")
    if mode == "text":
        return replace_paths(text, replacements).encode()
    if mode == "json":
        value = json.loads(text)
    elif mode == "xci_metadata":
        instance = json.loads(text)["ip_inst"]
        value = {key: instance[key] for key in
                 ("xci_name", "component_reference", "ip_revision", "parameters", "boundary")
                 if key in instance}
    elif mode == "report_rows":
        csv.field_size_limit(MAX_BYTES)
        value = []
        for row in csv.DictReader(io.StringIO(text)):
            if row["ip_type"] != entry["ip_type"]:
                continue
            if entry.get("case_ids") and row["case_id"] not in entry["case_ids"]:
                continue
            for key in ("parameters", "coverage_targets", "metrics"):
                row[key] = json.loads(row[key])
            value.append(row)
        if not value:
            raise ValueError(f"No report rows selected: {entry['source']}")
    else:
        raise ValueError(f"Unknown export mode: {mode}")
    return json_bytes(replace_paths(value, replacements))


def selections(root):
    index = json.loads(read_small(root / "evidence/index.json"))
    if index["schema_version"] != 1:
        raise ValueError("Unsupported evidence index")
    for relative in index["issues"]:
        base = beneath(root / "evidence", relative)
        spec_path = base / "selection.json"
        spec_data = read_small(spec_path)
        spec = json.loads(spec_data)
        if spec["schema_version"] != 1:
            raise ValueError(f"Unsupported selection: {relative}")
        yield base, spec, spec_data


def source_entry(root, entry):
    if Path(entry["source"]).parts[0] not in {"runs", "reports", "tests", "configs", "tcl", "src"}:
        raise ValueError(f"Source is outside the evidence allowlist: {entry['source']}")
    return beneath(root, entry["source"])


def make_package(root, base, spec, spec_data):
    copies = {base / "selection.json": spec_data}
    records = []
    for entry in spec["files"]:
        target = beneath(base, entry["target"])
        if not RUN_ID.fullmatch(Path(entry["target"]).parts[0]):
            raise ValueError(f"Export needs its original run ID: {entry['target']}")
        if target in copies:
            raise ValueError(f"Duplicate export target: {target}")
        original = read_small(source_entry(root, entry))
        exported = transform(original, entry, spec["path_replacements"])
        if PRIVATE.search(exported.decode()):
            raise ValueError(f"Credential pattern in export: {target}")
        copies[target] = exported
        records.append({"path": entry["target"], "sha256": digest(exported),
                        "bytes": len(exported), "source": entry["source"],
                        "source_sha256": digest(original), "source_bytes": len(original),
                        "mode": entry["mode"]})
    manifest = {"schema_version": 1, "issue": spec["issue"],
                "selection_sha256": digest(spec_data),
                "path_replacements": spec["path_replacements"], "files": records}
    copies[base / "manifest.json"] = json_bytes(manifest)
    sums = "".join(f"{digest(data)}  {path.relative_to(base).as_posix()}\n"
                   for path, data in sorted(copies.items()))
    copies[base / "SHA256SUMS"] = sums.encode()
    return copies


def export(root):
    planned = {}
    for base, spec, raw in selections(root):
        planned.update(make_package(root, base, spec, raw))
    # Check all inputs and existing copies before creating any new evidence.
    for path, data in planned.items():
        if path.exists() and path.read_bytes() != data:
            raise ValueError(f"Existing evidence differs; use a new run directory: {path}")
    for path, data in planned.items():
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(data)
    print(f"Exported or checked {len(planned)} files.")


def verify(root, originals=False):
    issue_count = file_count = total_bytes = 0
    for base, spec, raw in selections(root):
        manifest_data = read_small(base / "manifest.json")
        manifest = json.loads(manifest_data)
        if manifest["selection_sha256"] != digest(raw) or manifest["issue"] != spec["issue"]:
            raise ValueError(f"Selection does not match manifest: {base}")
        entries = {entry["target"]: entry for entry in spec["files"]}
        if len(entries) != len(spec["files"]) or set(entries) != {r["path"] for r in manifest["files"]}:
            raise ValueError(f"Export list does not match manifest: {base}")
        if len(manifest["files"]) != len(entries):
            raise ValueError(f"Repeated manifest entry: {base}")
        expected = {"manifest.json": digest(manifest_data), "selection.json": digest(raw)}
        for record in manifest["files"]:
            relative = record["path"]
            data = read_small(beneath(base, relative))
            if digest(data) != record["sha256"] or len(data) != record["bytes"]:
                raise ValueError(f"Public evidence changed: {base / relative}")
            if not RUN_ID.fullmatch(Path(relative).parts[0]):
                raise ValueError(f"Missing run timestamp: {relative}")
            entry = entries[relative]
            if record["source"] != entry["source"] or record["mode"] != entry["mode"]:
                raise ValueError(f"Source mapping changed: {relative}")
            if originals:
                source = read_small(source_entry(root, entry))
                if digest(source) != record["source_sha256"] or len(source) != record["source_bytes"]:
                    raise ValueError(f"Original evidence changed: {entry['source']}")
                if transform(source, entry, spec["path_replacements"]) != data:
                    raise ValueError(f"Export no longer matches original: {relative}")
            expected[relative] = digest(data)
            total_bytes += len(data)
            file_count += 1
        actual = {}
        for line in read_small(base / "SHA256SUMS").decode().splitlines():
            checksum, relative = line.split("  ", 1)
            if relative in actual:
                raise ValueError(f"Duplicate checksum: {relative}")
            beneath(base, relative)
            actual[relative] = checksum
        if actual != expected:
            raise ValueError(f"SHA256SUMS does not cover the package: {base}")
        public = {str(p.relative_to(base)) for p in base.rglob("*") if p.is_file()}
        if public != set(expected) | {"README.md", "SHA256SUMS"}:
            raise ValueError(f"Unlisted or missing evidence file: {base}")
        issue_count += 1
    print(f"Verified {issue_count} issues, {file_count} evidence files, {total_bytes} bytes."
          + (" Original sources match." if originals else " Local runs are not required."))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--export", action="store_true")
    action.add_argument("--verify", action="store_true")
    parser.add_argument("--check-sources", action="store_true",
                        help="Also compare each copy with the author's local runs/reports")
    args = parser.parse_args()
    if args.check_sources and not args.verify:
        parser.error("--check-sources requires --verify")
    try:
        if args.export:
            export(ROOT)
        verify(ROOT, originals=args.check_sources or args.export)
    except (OSError, ValueError, KeyError, csv.Error) as exc:
        print(f"Evidence check failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

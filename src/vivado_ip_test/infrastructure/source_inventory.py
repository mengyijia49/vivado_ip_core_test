from pathlib import Path

from vivado_ip_test.infrastructure.hashing import sha256_file


def source_inventory(root: Path) -> dict[str, str]:
    return {
        str(source.relative_to(root)): sha256_file(source)
        for dirname, suffixes in (
            ("src", {".py", ".tpl"}), ("scripts", {".py"}), ("tcl", {".tcl"}),
        )
        for source in sorted((root / dirname).rglob("*"))
        if source.is_file() and source.suffix in suffixes
    }

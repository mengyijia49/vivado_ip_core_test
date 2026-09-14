from pathlib import Path


def output_files_match(expected_path: Path, actual_path: Path) -> bool:
    if not expected_path.exists() or not actual_path.exists():
        return False
    expected = expected_path.read_text().splitlines()
    actual = actual_path.read_text().splitlines()
    return bool(expected) and expected == actual

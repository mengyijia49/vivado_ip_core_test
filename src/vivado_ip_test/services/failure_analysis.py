"""从完整保留的输入输出定位首个差异，不自动归因为 IP 缺陷。"""

import json
from itertools import zip_longest
from pathlib import Path


def analyze_outputs(run_dir: Path) -> dict[str, object]:
    expected_path = run_dir / "vectors/expected_output.txt"
    actual_path = run_dir / "outputs/actual_output.txt"
    evidence: dict[str, object] = {"classification": "UNTRIAGED", "kind": "no_numeric_difference"}
    if not expected_path.is_file() or not actual_path.is_file():
        evidence["kind"] = "missing_output_artifact"
        return evidence
    with expected_path.open() as expected_file, actual_path.open() as actual_file:
        for index, (expected, actual) in enumerate(zip_longest(expected_file, actual_file)):
            expected = None if expected is None else expected.strip()
            actual = None if actual is None else actual.strip()
            if expected == actual:
                continue
            evidence.update({
                "kind": "missing_output" if actual is None else
                        "extra_output" if expected is None else "value_mismatch",
                "output_index": index, "expected": expected, "actual": actual,
                "contains_unknown_bits": actual is not None and any(bit not in "01" for bit in actual),
            })
            try:
                schedule = json.loads((run_dir / "vectors/schedule.json").read_text())
                vector_index = schedule["transaction_vector_indices"][index]
                vectors = json.loads((run_dir / "vectors/vectors.json").read_text())
                evidence["vector_index"] = vector_index
                evidence["input_vector"] = vectors[vector_index]
                evidence["timing_mode"] = schedule["timing_mode"]
            except (OSError, ValueError, KeyError, IndexError, TypeError):
                evidence["input_mapping_available"] = False
            break
    return evidence

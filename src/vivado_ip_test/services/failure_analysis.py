"""保留首个差异并扫描后续异常，不自动归因为 IP 缺陷。"""

import json
from pathlib import Path

from vivado_ip_test.infrastructure.output import iter_output_differences
from vivado_ip_test.services.failure_context import FailureContext
from vivado_ip_test.services.failure_groups import FailureGroups


def analyze_outputs(run_dir: Path, *, group_limit: int = 256) -> dict[str, object]:
    expected_path = run_dir / "vectors/expected_output.txt"
    actual_path = run_dir / "outputs/actual_output.txt"
    evidence: dict[str, object] = {"classification": "UNTRIAGED", "kind": "no_numeric_difference"}
    mask_path = run_dir / "vectors/expected_mask.txt"
    masked = mask_path.exists()
    layout = None
    try:
        manifest = json.loads((run_dir / "manifest.json").read_text())
        if isinstance(manifest, dict):
            masked |= "expected_mask" in manifest.get("artifacts", {})
            layout = manifest.get("output_layout")
    except (OSError, ValueError, TypeError):
        pass
    groups = FailureGroups(layout, group_limit)
    mapping, first = None, True

    def record(difference):
        nonlocal first, mapping
        index = difference.get("output_index")
        context = {"phase": "artifact", "input_mapping_available": False}
        if index is not None:
            if mapping is None:
                mapping = FailureContext(run_dir)
            context = mapping.brief(index)
        if first:
            evidence.update(difference)
            if index is not None:
                evidence.update(mapping.detailed(index))
            first = False
        groups.add(difference, context)

    try:
        for difference in iter_output_differences(expected_path, actual_path, mask_path=mask_path if masked else None):
            record(difference)
    except (OSError, UnicodeError) as exc:
        record({"kind": "unreadable_output_artifact", "error_type": type(exc).__name__})
    evidence["difference_summary"] = groups.as_dict()
    return evidence

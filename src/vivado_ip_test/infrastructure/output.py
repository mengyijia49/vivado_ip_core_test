from pathlib import Path
from contextlib import ExitStack, closing
from itertools import zip_longest
import re


_BINARY_ROW = re.compile(r"[01]+")


def iter_output_differences(expected_path: Path, actual_path: Path, *, mask_path: Path | None = None):
    if not expected_path.is_file() or not actual_path.is_file():
        yield {"kind": "missing_output_artifact"}
        return
    if mask_path is not None and not mask_path.is_file():
        yield {"kind": "missing_mask_artifact"}
        return
    checked = rows = 0
    has_row_issue = False
    with ExitStack() as stack:
        streams = [stack.enter_context(p.open()) for p in (expected_path, actual_path)]
        if mask_path is not None:
            streams.append(stack.enter_context(mask_path.open()))
        for index, raw in enumerate(zip_longest(*streams)):
            expected, actual = (None if s is None else s.rstrip("\r\n") for s in raw[:2])
            mask = None if mask_path is None or raw[2] is None else raw[2].rstrip("\r\n")
            # Wide unmasked PASS rows need no per-bit Python loop or temporary mask.
            if mask_path is None and expected is not None and expected == actual and _BINARY_ROW.fullmatch(expected):
                checked += len(expected)
                rows += 1
                continue
            kind = None
            if expected is None and actual is not None:
                kind = "extra_output"
            elif actual is None and expected is not None:
                kind = "missing_output"
            elif expected is None or mask_path is not None and (
                    mask is None or len(mask) != len(expected) or any(b not in "01" for b in mask)):
                kind = "invalid_output_mask"
            elif not expected or any(b not in "01" for b in expected):
                kind = "invalid_expected_output"
            elif len(actual) != len(expected) or any(b.upper() not in "01UXZWLH-" for b in actual):
                kind = "invalid_actual_output"
            else:
                active = mask if mask is not None else "1" * len(expected)
                checked += active.count("1")
                if any(e != a for e, a, bit in zip(expected, actual, active) if bit == "1"):
                    kind = "value_mismatch"
            rows += 1
            if kind:
                has_row_issue = True
                yield {"kind": kind, "output_index": index, "expected": expected, "actual": actual,
                       **({"expected_mask": mask} if mask_path is not None else {}),
                       "contains_unknown_bits": actual is not None and any(b not in "01" for b in actual)}
    if not rows:
        yield {"kind": "empty_output_artifact"}
    elif not checked and not has_row_issue:
        yield {"kind": "no_defined_output_bits"}


def first_output_difference(expected_path: Path, actual_path: Path, *, mask_path: Path | None = None):
    with closing(iter_output_differences(expected_path, actual_path, mask_path=mask_path)) as differences:
        return next(differences, None)


def output_files_match(expected_path: Path, actual_path: Path, *, mask_path: Path | None = None) -> bool:
    return first_output_difference(expected_path, actual_path, mask_path=mask_path) is None


def output_fields_within_tolerance(expected_path: Path, actual_path: Path, tolerance_path: Path,
                                   field_widths: tuple[int, ...],
                                   signed_fields: tuple[bool, ...] = ()) -> bool:
    """Compare packed binary fields using a distance limit per field and row."""
    if not all(path.is_file() for path in (expected_path, actual_path, tolerance_path)):
        return False
    if signed_fields and len(signed_fields) != len(field_widths):
        return False
    signed_fields = signed_fields or (False,) * len(field_widths)
    width = sum(field_widths)
    with expected_path.open() as expected_file, actual_path.open() as actual_file, \
            tolerance_path.open() as tolerance_file:
        rows = 0
        for raw_expected, raw_actual, raw_tolerance in zip_longest(
                expected_file, actual_file, tolerance_file):
            if None in (raw_expected, raw_actual, raw_tolerance):
                return False
            expected = raw_expected.rstrip("\r\n")
            actual = raw_actual.rstrip("\r\n")
            tolerance = raw_tolerance.rstrip("\r\n")
            if any(len(row) != width or not _BINARY_ROW.fullmatch(row)
                   for row in (expected, actual, tolerance)):
                return False
            offset = 0
            for field_width, signed_field in zip(field_widths, signed_fields):
                end = offset + field_width
                actual_value = int(actual[offset:end], 2)
                expected_value = int(expected[offset:end], 2)
                if signed_field:
                    sign = 1 << (field_width - 1)
                    actual_value -= (1 << field_width) if actual_value & sign else 0
                    expected_value -= (1 << field_width) if expected_value & sign else 0
                if abs(actual_value - expected_value) > int(tolerance[offset:end], 2):
                    return False
                offset = end
            rows += 1
    return rows > 0

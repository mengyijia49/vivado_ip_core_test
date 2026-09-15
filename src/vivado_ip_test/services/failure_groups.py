from collections import Counter

from vivado_ip_test.infrastructure.output_layout import output_field_slices


class FailureGroups:
    """有界保存分组示例；所有行仍扫描，原始输出不截断。"""

    def __init__(self, layout, limit=256):
        if type(limit) is not int or limit < 1:
            raise ValueError("Failure group limit must be a positive integer")
        self.limit, self.groups, self.kinds = limit, {}, Counter()
        self.rows = self.artifact_issues = self.omitted = self.unmapped = 0
        self.complete = True
        self.layout_issues = Counter()
        try:
            self.fields = output_field_slices(layout)
        except ValueError:
            self.fields = ()

    def differing_fields(self, difference):
        if difference["kind"] != "value_mismatch":
            return (None,)
        expected, actual = difference["expected"], difference["actual"]
        if not self.fields:
            self.layout_issues["layout_missing_or_invalid"] += 1
            return ("packed_output",)
        if self.fields[-1][2] != len(expected):
            self.layout_issues["layout_width_mismatch"] += 1
            return ("packed_output",)
        mask = difference.get("expected_mask")
        names = []
        for name, start, stop in self.fields:
            e, a = expected[start:stop], actual[start:stop]
            if e != a and (mask is None or any(x != y for x, y, bit in zip(e, a, mask[start:stop]) if bit == "1")):
                names.append(name)
        return tuple(names)

    @staticmethod
    def preview(difference):
        result, truncated = dict(difference), []
        for key in ("expected", "actual", "expected_mask"):
            value = result.get(key)
            if isinstance(value, str) and len(value) > 256:
                result[key] = value[:256]
                result[key+"_width"] = len(value)
                truncated.append(key)
        if truncated:
            result["truncated_row_fields"] = truncated
        return result

    def add(self, difference, context):
        kind = difference["kind"]
        index = difference.get("output_index")
        self.kinds[kind] += 1
        if index is None:
            self.artifact_issues += 1
        else:
            self.rows += 1
            self.unmapped += int(not context["input_mapping_available"])
        if kind in ("missing_output_artifact", "missing_mask_artifact", "unreadable_output_artifact"):
            self.complete = False
        for field in self.differing_fields(difference):
            route = context.get("stream_route", {})
            key = (kind, context["phase"], field, route.get("input_lane"), route.get("output_port"))
            if key not in self.groups:
                if len(self.groups) >= self.limit:
                    self.omitted += 1
                    continue
                self.groups[key] = {"kind": kind, "phase": context["phase"], "output_field": field,
                    "count": 0, "first_output_index": index, "last_output_index": index,
                    "first_context": context, "first_difference": self.preview(difference),
                    "example_output_indices": []}
            group = self.groups[key]
            group["count"] += 1
            group["last_output_index"] = index
            if index is not None and len(group["example_output_indices"]) < 3:
                group["example_output_indices"].append(index)

    def as_dict(self):
        return {"schema_version": 1, "grouping": "kind_phase_output_field_route:1.0",
            "classification": "OBSERVATION_GROUPS_NOT_BUG_COUNTS", "all_rows_visited": self.complete,
            "difference_rows": self.rows, "artifact_issues": self.artifact_issues,
            "difference_kind_counts": dict(self.kinds), "rows_without_input_mapping": self.unmapped,
            "layout_issue_rows": dict(self.layout_issues), "group_limit": self.limit,
            "retained_group_count": len(self.groups), "groups_truncated": bool(self.omitted),
            "omitted_group_memberships": self.omitted, "groups": list(self.groups.values())}

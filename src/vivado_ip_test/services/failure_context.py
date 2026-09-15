from bisect import bisect_right
import json


class FailureContext:
    """按生成时的映射查找上下文，不从输出位置猜测因果关系。"""

    def __init__(self, run_dir):
        self.schedule, self.records, self.resets = {}, [], []
        try:
            schedule = json.loads((run_dir / "vectors/schedule.json").read_text())
            if not isinstance(schedule, dict):
                raise ValueError("Invalid schedule")
            filename = "cycles.json" if schedule.get("mapping_kind") == "sampled_cycle" else "vectors.json"
            records = json.loads((run_dir / "vectors" / filename).read_text())
            if not isinstance(records, list):
                raise ValueError("Invalid input records")
            self.schedule, self.records = schedule, records
            if schedule.get("mapping_kind") == "register_operation":
                self.resets = [i for i, row in enumerate(records) if isinstance(row, dict)
                    and isinstance(row.get("command"), dict) and row["command"].get("action") == 3]
        except (OSError, ValueError, TypeError):
            pass

    def locate(self, index):
        if self.schedule.get("mapping_kind") == "sampled_cycle":
            position = index
        else:
            position = self.schedule["transaction_vector_indices"][index]
        if type(position) is not int or not 0 <= position < len(self.records):
            raise ValueError("Invalid input position")
        record = self.records[position]
        if not isinstance(record, dict):
            raise ValueError("Invalid input record")
        return position, record

    def brief(self, index):
        try:
            position, record = self.locate(index)
            phase = record.get("phase", self.schedule.get("mapping_kind", "transaction"))
            if not isinstance(phase, str) or not 1 <= len(phase) <= 256:
                raise ValueError("Invalid phase")
            result = {"phase": phase, "input_record_index": position, "input_mapping_available": True}
            if "output_mapping" in self.schedule:
                try:
                    route = self.schedule["output_mapping"][index]
                    values = {key: route[key] for key in ("input_lane", "output_port")}
                    if any(type(value) is not int or value < 0 for value in values.values()):
                        raise ValueError("Invalid output route")
                    result["stream_route"] = values
                except (KeyError, IndexError, ValueError, TypeError):
                    result["route_mapping_available"] = False
            if self.schedule.get("mapping_kind") == "register_operation":
                reset_index = bisect_right(self.resets, position)-1
                result["preceding_reset_operation_index"] = self.resets[reset_index] if reset_index >= 0 else None
                result["causal_input_not_identified"] = True
            elif self.schedule.get("mapping_kind") == "sampled_cycle":
                result["causal_input_not_identified"] = True
            return result
        except (KeyError, IndexError, ValueError, TypeError):
            return {"phase": "unmapped", "input_mapping_available": False}

    def detailed(self, index):
        try:
            position, record = self.locate(index)
            timing = self.schedule["timing_mode"]
            if self.schedule.get("mapping_kind") == "sampled_cycle":
                return {"sampled_cycle": record, "preceding_cycles": self.records[max(0, position-8):position],
                        "timing_mode": timing, "causal_input_not_identified": True}
            result = {"vector_index": position, "input_vector": record, "timing_mode": timing}
            if self.schedule.get("mapping_kind") == "register_operation":
                result.update(operation_index=position, preceding_operations=self.records[max(0, position-8):position],
                    preceding_reset_operation_index=self.brief(index).get("preceding_reset_operation_index"),
                    generated_sample_index=record.get("vector_index"), causal_input_not_identified=True)
            return result
        except (KeyError, IndexError, ValueError, TypeError):
            return {"input_mapping_available": False}

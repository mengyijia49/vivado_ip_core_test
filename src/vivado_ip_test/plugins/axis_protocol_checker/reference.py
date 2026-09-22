from collections import Counter


STATUS_BITS = {
    "legal": None,
    "tvalid_after_reset": 0,
    "tid_changed": 1,
    "tdest_changed": 2,
    "tkeep_changed": 3,
    "tdata_changed": 4,
    "tlast_changed": 5,
    "tstrb_changed": 6,
    "tvalid_dropped": 7,
    "max_wait_exceeded": 8,
    "tuser_changed": 9,
    "tkeep_tstrb_conflict": 10,
    "aclken_pauses_wait_counter": None,
}


def applicable_scenarios(parameters):
    scenarios = ["legal", "tkeep_tstrb_conflict"]
    if not parameters["has_system_reset"]:
        scenarios.append("tvalid_after_reset")
    if parameters["has_tready"]:
        scenarios.extend(("tdata_changed", "tvalid_dropped"))
        if parameters["tid_width"]:
            scenarios.append("tid_changed")
        if parameters["tdest_width"]:
            scenarios.append("tdest_changed")
        if parameters["has_tkeep"]:
            scenarios.append("tkeep_changed")
        if parameters["has_tlast"]:
            scenarios.append("tlast_changed")
        if parameters["has_tstrb"]:
            scenarios.append("tstrb_changed")
        if parameters["tuser_width"]:
            scenarios.append("tuser_changed")
        if parameters["max_waits"]:
            scenarios.append("max_wait_exceeded")
            if parameters["has_aclken"]:
                scenarios.append("aclken_pauses_wait_counter")
    if not (parameters["has_tkeep"] and parameters["has_tstrb"]):
        scenarios.remove("tkeep_tstrb_conflict")
    return tuple(scenarios)


def prepare_operations(parameters, verification):
    scenarios = applicable_scenarios(parameters)
    return [{"scenario": scenarios[index % len(scenarios)]}
            for index in range(verification.case_budget)]


class AxisProtocolCheckerReference:
    def __init__(self):
        self.event_counts = Counter()

    def evaluate(self, operations):
        rows = []
        for operation in operations:
            scenario = operation["scenario"]
            bit = STATUS_BITS[scenario]
            status = 0 if bit is None else 1 << bit
            rows.append({"status": status, "asserted": int(status != 0)})
            self.event_counts[scenario] += 1
        return rows

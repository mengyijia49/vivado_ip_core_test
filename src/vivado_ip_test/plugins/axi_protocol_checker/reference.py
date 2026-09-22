from collections import Counter


SCENARIOS = (
    ("legal_read_write", None),
    ("aw_reserved_burst", 2),
    ("aw_invalid_wrap_length", 6),
    ("aw_transfer_too_wide", 7),
    ("awvalid_dropped", 19),
    ("awaddr_changed", 9),
    ("ar_reserved_burst", 39),
    ("ar_invalid_wrap_length", 43),
    ("ar_transfer_too_wide", 44),
    ("arvalid_dropped", 56),
    ("araddr_changed", 46),
)

EXPECTED_BITS = dict(SCENARIOS)
EXPECTED_BITS.update({"aw_fixed_too_long": 5, "ar_fixed_too_long": 42})


def expected_status(scenario):
    bit = EXPECTED_BITS[scenario]
    return 0 if bit is None else 1 << bit


class AxiProtocolCheckerReference:
    def __init__(self):
        self.event_counts = Counter()

    def evaluate(self, operations):
        outputs = []
        for operation in operations:
            scenario = operation["scenario"]
            status = expected_status(scenario)
            outputs.append({"status": status, "asserted": int(status != 0)})
            self.event_counts[scenario] += 1
        return outputs

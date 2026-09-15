from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import Port


STATUS_DEFAULTS = {"data_count_width": 0, "prog_full_assert": 0, "prog_full_negate": 0,
                   "prog_empty_assert": 0, "prog_empty_negate": 0}


def validate_status(p):
    fwft = p["read_mode"] == "fwft"
    count_bits = p["depth"].bit_length() - 1 + int(fwft)
    if p["data_count_width"] > count_bits:
        raise PluginError("FIFO data_count_width exceeds the count bus width")
    full_min, full_max = (5, p["depth"] - 1) if fwft else (3, p["depth"] - 2)
    empty_min, empty_max = (4, p["depth"] - 1) if fwft else (2, p["depth"] - 3)
    for flag, minimum, maximum in (("full", full_min, full_max), ("empty", empty_min, empty_max)):
        assertion, negation = p[f"prog_{flag}_assert"], p[f"prog_{flag}_negate"]
        if not assertion:
            if negation:
                raise PluginError(f"prog_{flag}_negate requires an enabled assert threshold")
            continue
        if not minimum <= assertion <= maximum:
            raise PluginError(f"prog_{flag}_assert must be between {minimum} and {maximum}")
        if negation:
            valid = minimum <= negation < assertion if flag == "full" else assertion < negation <= maximum
            if not valid:
                raise PluginError(f"Invalid prog_{flag} hysteresis thresholds")


def status_ports(p):
    ports = [Port("data_count", p["data_count_width"])] if p["data_count_width"] else []
    ports += [Port("prog_" + flag, scalar=True) for flag in ("full", "empty") if p[f"prog_{flag}_assert"]]
    return tuple(ports)


def status_settings(p):
    settings, metadata = {}, {}
    if p["data_count_width"]:
        settings["Data_Count_Width"] = p["data_count_width"]
        metadata["C_DATA_COUNT_WIDTH"] = p["data_count_width"]
        metadata["C_USE_FWFT_DATA_COUNT"] = int(p["read_mode"] == "fwft")
    for flag in ("full", "empty"):
        assertion, negation = p[f"prog_{flag}_assert"], p[f"prog_{flag}_negate"]
        code = 0 if not assertion else 2 if negation else 1
        metadata[f"C_PROG_{flag.upper()}_TYPE"] = code
        if code:
            kind = "Multiple" if negation else "Single"
            suffix = "Constants" if negation else "Constant"
            settings[f"Programmable_{flag.title()}_Type"] = f"{kind}_Programmable_{flag.title()}_Threshold_{suffix}"
            settings[f"{flag.title()}_Threshold_Assert_Value"] = assertion
            metadata[f"C_PROG_{flag.upper()}_THRESH_ASSERT_VAL"] = assertion
            metadata[f"C_PROG_{flag.upper()}_THRESH_NEGATE_VAL"] = (
                negation or assertion + (-1 if flag == "full" else 1))
            if negation:
                settings[f"{flag.title()}_Threshold_Negate_Value"] = negation
    return settings, metadata


class FifoStatusModel:
    def __init__(self, model, parameters):
        self.model = model
        self.p = dict(parameters)
        self.event_counts = model.event_counts
        self.prog_full = False
        self.prog_empty = True

    def step(self, inputs):
        p = self.p
        old_count = len(self.model.words)
        result = self.model.step(inputs)
        count = len(self.model.words)
        if inputs["srst"]:
            self.prog_full, self.prog_empty = False, True
        else:
            if p["prog_full_assert"]:
                if old_count >= p["prog_full_assert"]:
                    self.prog_full = True
                elif old_count < (p["prog_full_negate"] or p["prog_full_assert"]):
                    self.prog_full = False
            if p["prog_empty_assert"]:
                if old_count <= p["prog_empty_assert"]:
                    self.prog_empty = True
                elif old_count > (p["prog_empty_negate"] or p["prog_empty_assert"]):
                    self.prog_empty = False
        if p["data_count_width"]:
            width = p["data_count_width"]
            full_width = p["depth"].bit_length() - 1 + int(p["read_mode"] == "fwft")
            result["data_count"] = (count >> (full_width - width)) & ((1 << width) - 1)
            self.event_counts["data_count_checked"] += 1
        for flag, value in (("full", self.prog_full), ("empty", self.prog_empty)):
            if p[f"prog_{flag}_assert"]:
                result[f"prog_{flag}"] = int(value)
                self.event_counts[f"prog_{flag}_{'asserted' if value else 'deasserted'}"] += 1
        return result


def status_prefix(p):
    mask = (1 << p["width"]) - 1
    targets = sorted({p[key] for key in STATUS_DEFAULTS if key.startswith("prog_") and p[key]})
    for target in targets:
        yield {"srst": 1}
        yield from ({"wr_en": 1, "din": i & mask} for i in range(target - 1))
        yield from ({} for _ in range(3))
        for _ in range(3):
            yield {"wr_en": 1, "din": mask}
            yield from ({} for _ in range(3))
            yield {"rd_en": 1}
            yield from ({} for _ in range(3))
        yield from ({"wr_en": 1, "din": i & mask} for i in range(3))
        yield from ({} for _ in range(3))
        for _ in range(3):
            yield {"rd_en": 1}
            yield from ({} for _ in range(3))
        yield {"srst": 1}

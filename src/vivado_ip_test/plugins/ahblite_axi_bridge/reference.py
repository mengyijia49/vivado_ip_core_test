from collections import Counter


def axi_attributes(hprot, non_secure):
    prot = ((1 - (hprot & 1)) << 2) | (int(non_secure) << 1) | ((hprot >> 1) & 1)
    cache = (hprot >> 2) & 3
    return prot, cache


def write_strobe(address, size, data_width, narrow_burst):
    lanes = data_width // 8
    if not narrow_burst:
        return (1 << lanes) - 1
    return ((1 << (1 << size)) - 1) << (address % lanes)


def read_value(address, data_width, salt):
    mask = (1 << data_width) - 1
    return ((address * 0x9E3779B1) ^ (salt * 0xA5A55A5A) ^ (mask >> 3)) & mask


class AhbLiteAxiReference:
    def __init__(self, parameters):
        self.p = dict(parameters)
        self.event_counts = Counter()

    def expected(self, operations):
        rows = []
        lanes = self.p["data_width"] // 8
        for operation in operations:
            write = operation["kind"] == "write"
            strobe = write_strobe(operation["address"], operation["size"],
                                   self.p["data_width"], self.p["narrow_burst"]) if write else 0
            data = operation["data"] if write else operation["read_data"]
            rows.append({"write": int(write), "address": operation["address"],
                         "data": data, "strobe": strobe,
                         "error": int(operation["response"] != 0)})
            self.event_counts[operation["kind"]] += 1
            self.event_counts[f"response_{operation['response']}"] += 1
            self.event_counts[f"size_{1 << operation['size']}_bytes"] += 1
            assert 0 <= strobe < 1 << lanes
        return rows


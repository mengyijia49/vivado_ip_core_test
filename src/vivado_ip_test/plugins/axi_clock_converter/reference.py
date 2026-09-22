from collections import Counter


CHANNELS = ("aw", "w", "b", "ar", "r")


def _mask(width):
    return (1 << width) - 1


def transaction(channel, variant, p, hold=0):
    width, ident_width, user_width = p["data_width"], p["id_width"], p["user_width"]
    common = {"channel": CHANNELS.index(channel), "id": (variant * 3 + 1) & _mask(ident_width),
              "addr": (0x10203040 ^ (variant * 0x11104)) & _mask(p["address_width"]),
              "len": (variant * 7 + 3) & 0xFF, "size": width.bit_length() - 4,
              "burst": 2 if variant % 3 == 2 else 1, "lock": variant & 1,
              "cache": (variant * 5 + 3) & 15, "prot": (variant * 3 + 1) & 7,
              "region": (variant * 7 + 2) & 15, "qos": (variant * 11 + 4) & 15,
              "data": (_mask(width) ^ (0xA55A + variant * 0x10101)) & _mask(width),
              "strb": (_mask(width // 8) ^ (variant & 3)) or 1,
              "last": int(variant % 3 != 1), "resp": variant & 3,
              "user": (_mask(user_width) ^ (variant * 13)) & _mask(user_width),
              "hold": hold}
    return common


def prepare_operations(samples, p):
    operations = []
    for variant in range(4):
        for index, channel in enumerate(CHANNELS):
            operations.append(transaction(channel, variant, p, (variant + index) % 4))
    for index, sample in enumerate(samples):
        channel = CHANNELS[sample["sample_channel"] % len(CHANNELS)]
        item = transaction(channel, index + 4, p, sample["sample_hold"])
        item.update({"id": sample["sample_id"], "addr": sample["sample_address"],
                     "data": sample["sample_data"], "user": sample["sample_user"]})
        operations.append(item)
    return operations


class AxiClockConverterReference:
    def __init__(self):
        self.event_counts = Counter()

    def evaluate(self, operations):
        result = []
        relevant = {
            0: {"id", "addr", "len", "size", "burst", "lock", "cache", "prot", "region", "qos", "user"},
            1: {"data", "strb", "last", "user"}, 2: {"id", "resp", "user"},
            3: {"id", "addr", "len", "size", "burst", "lock", "cache", "prot", "region", "qos", "user"},
            4: {"id", "data", "last", "resp", "user"},
        }
        for item in operations:
            self.event_counts[CHANNELS[item["channel"]]] += 1
            if item["hold"]:
                self.event_counts["backpressured"] += 1
            result.append({name: item[name] if name == "channel" or name in relevant[item["channel"]]
                           else 0 for name in item if name != "hold"})
        return result

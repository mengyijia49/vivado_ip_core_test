from collections import Counter, deque

from vivado_ip_test.plugins.common.cycle import DefinedBits, decode


def byte_width(width):
    return ((width + 7) // 8) * 8


def unpack_complex(value, width):
    mask = (1 << width) - 1
    return (decode(value & mask, width, True),
            decode((value >> byte_width(width)) & mask, width, True))


def product_components(a, b):
    ar, ai = a
    br, bi = b
    return ar * br - ai * bi, ar * bi + ai * br


def quantize(value, full_width, output_width, round_carry=None):
    shift = full_width - output_width
    if round_carry is not None:
        if shift < 1:
            raise ValueError("Rounding requires a shortened result")
        value += (1 << (shift - 1)) - 1 + round_carry
    # Interpret the selected field before extending it to the AXI byte boundary.
    bits = (value >> shift) & ((1 << output_width) - 1)
    return decode(bits, output_width, True) & ((1 << byte_width(output_width)) - 1)


class ComplexMultiplierModel:
    def __init__(self, parameters, latency, output_ports):
        self.p = parameters
        self.outputs = output_ports
        self.delay = max(0, latency - 1)
        self.history = deque([None] * self.delay)
        self.output = None
        self.event_counts = Counter()

    def result(self, inputs):
        p = self.p
        channels = ("a", "b", "ctrl") if p["rounding"] == "Random_Rounding" else ("a", "b")
        valid = int(all(inputs[f"s_axis_{channel}_tvalid"] for channel in channels))
        values = {"m_axis_dout_tvalid": valid}
        if not valid:
            self.event_counts["invalid_input_cycles"] += 1
            return values
        self.event_counts["valid_input_operations"] += 1
        a = unpack_complex(inputs["s_axis_a_tdata"], p["a_width"])
        b = unpack_complex(inputs["s_axis_b_tdata"], p["b_width"])
        real, imaginary = product_components(a, b)
        carry = inputs["s_axis_ctrl_tdata"] & 1 if "ctrl" in channels else None
        full = p["a_width"] + p["b_width"] + 1
        out = p["output_width"]
        values["m_axis_dout_tdata"] = (quantize(real, full, out, carry) |
            (quantize(imaginary, full, out, carry) << byte_width(out)))
        if carry is not None:
            self.event_counts[f"round_carry_{carry}"] += 1
            shift = full - out
            self.event_counts["rounding_tie_components"] += sum(
                (value & ((1 << shift) - 1)) == 1 << (shift - 1) for value in (real, imaginary))
        lasts = {ch: inputs[f"s_axis_{ch}_tlast"] for ch in channels if p[f"{ch}_last"]}
        mode = p["last_mode"]
        if mode != "Null":
            values["m_axis_dout_tlast"] = (int(any(lasts.values())) if mode == "OR_all_TLASTs" else
                int(all(lasts.values())) if mode == "AND_all_TLASTs" else
                lasts[{"Pass_A_TLAST": "a", "Pass_B_TLAST": "b", "Pass_CTRL_TLAST": "ctrl"}[mode]])
        offset = user = 0
        for ch in channels:
            width = p[f"{ch}_user_width"]
            if width:
                user |= inputs[f"s_axis_{ch}_tuser"] << offset
                offset += width
        if offset:
            values["m_axis_dout_tuser"] = user
        return values

    def step(self, inputs):
        if inputs.get("aclken", 1):
            result = self.result(inputs)
            self.history.append(result)
            self.output = self.history.popleft()
        else:
            self.event_counts["clock_enable_holds"] += 1
        result = self.output or {"m_axis_dout_tvalid": 0}
        valid = result["m_axis_dout_tvalid"]
        self.event_counts["valid_output_samples"] += valid
        return {port.name: result[port.name] if port.name == "m_axis_dout_tvalid" or valid else
                DefinedBits(0, 0, "output_tvalid_low") for port in self.outputs}

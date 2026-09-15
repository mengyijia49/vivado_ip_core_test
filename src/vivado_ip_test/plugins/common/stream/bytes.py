from dataclasses import dataclass

from vivado_ip_test.plugins.common.cycle import Port


@dataclass(frozen=True)
class ByteExpectation:
    ports: tuple[Port, ...]
    frames: tuple[dict[str, int], ...]
    payload: tuple[Port, ...]
    count: int

    def __iter__(self):
        # Wide input beats can expand into millions of byte records.
        return byte_records(self.frames, self.payload, self.ports)


def token_ports(payload):
    widths = {port.name: port.width for port in payload}
    byte_count = widths["tdata"] // 8
    ports = [Port("end_packet", scalar=True), Port("data_byte", scalar=True), Port("data", 8)]
    for name in ("tid", "tdest"):
        if name in widths:
            ports.append(Port(name, widths[name]))
    if "tuser" in widths:
        if widths["tuser"] % byte_count:
            raise ValueError("TUSER width must contain an integer number of bits per byte")
        ports.append(Port("tuser", widths["tuser"] // byte_count))
    return tuple(ports)


def expected_bytes(frames, payload):
    ports = token_ports(payload)
    nbytes = next(p.width for p in payload if p.name == "tdata") // 8
    full = (1 << nbytes) - 1
    frames = tuple(dict(frame) for frame in frames)
    count = 0
    for frame in frames:
        keep = frame.get("tkeep", full)
        if frame.get("tstrb", keep) & ~keep & full:
            raise ValueError("Reserved TKEEP=0 TSTRB=1 input qualifier")
        count += keep.bit_count() + bool(frame.get("tlast", 0))
    return ByteExpectation(ports, frames, payload, count)


def byte_records(frames, payload, ports):
    widths = {port.name: port.width for port in payload}
    nbytes = widths["tdata"] // 8
    full = (1 << nbytes) - 1
    user_width = widths.get("tuser", 0) // nbytes
    for index, frame in enumerate(frames):
        keep = frame.get("tkeep", full)
        strb = frame.get("tstrb", keep)
        common = {name: frame[name] for name in ("tid", "tdest") if name in widths}
        for lane in range(nbytes):
            if not keep >> lane & 1:
                continue
            data_byte = strb >> lane & 1
            row = {"end_packet": 0, "data_byte": data_byte,
                   "data": frame["tdata"] >> (8 * lane) & 255, **common}
            mask = {port.name: port.limit for port in ports}
            if not data_byte:
                mask["data"] = 0
            if user_width:
                row["tuser"] = frame["tuser"] >> (user_width * lane) & ((1 << user_width) - 1)
            yield row, mask, index + 1
        if frame.get("tlast", 0):
            row = {port.name: 0 for port in ports}
            row.update(end_packet=1, **common)
            mask = {port.name: port.limit if port.name in {"end_packet", "tid", "tdest"}
                    else 0 for port in ports}
            yield row, mask, index + 1


def bit_fields(payload):
    left = sum(port.width for port in payload)
    fields = {}
    for port in payload:
        left -= port.width
        fields[port.name] = (left, port.width)
    return fields


def raw_output_tokens(path, payload):
    """Decode the retained DUT beats independently of the generated HDL decoder."""
    fields = bit_fields(payload)
    widths = {port.name: port.width for port in payload}
    total = sum(widths.values())
    nbytes = widths["tdata"] // 8
    user_width = widths.get("tuser", 0) // nbytes

    def known(bits):
        if not bits or set(bits) - {"0", "1"}:
            raise ValueError("Unknown control or qualified stream data")
        return bits

    with path.open() as source:
        for line in source:
            text = line.strip()
            if len(text) != total:
                raise ValueError("Invalid raw stream width")
            frame = {name: text[total - low - width:total - low] for name, (low, width) in fields.items()}
            keep = known(frame.get("tkeep", "1" * nbytes))
            strb = known(frame.get("tstrb", keep))
            if any(k == "0" and s == "1" for k, s in zip(keep, strb)):
                raise ValueError("Reserved TKEEP=0 TSTRB=1 output qualifier")
            last = known(frame.get("tlast", "0"))
            common = "".join(known(frame[name]) for name in ("tid", "tdest") if name in frame)
            for lane in range(nbytes):
                if keep[-lane - 1] == "0":
                    continue
                data_byte = known(strb[-lane - 1])
                start = 8 * (nbytes - lane - 1)
                data = frame["tdata"][start:start + 8]
                if data_byte == "1":
                    known(data)
                user = ""
                if user_width:
                    start = user_width * (nbytes - lane - 1)
                    user = known(frame["tuser"][start:start + user_width])
                yield "0" + data_byte + data + common + user
            if last == "1":
                yield "1" + "0" * 9 + common + "0" * user_width

from collections.abc import Mapping
from dataclasses import dataclass

from vivado_ip_test.plugins.common.cycle import Port


PAYLOAD_RULES = {
    "data_bytes": range(1, 65), "id_width": range(0, 17),
    "dest_width": range(0, 17), "user_width": range(0, 65),
    "has_last": bool, "has_keep": bool, "has_strb": bool,
}


def payload_ports(p):
    ports = [Port("tdata", 8 * p["data_bytes"])]
    ports += [Port(name, p["data_bytes"]) for name, key in
              (("tstrb", "has_strb"), ("tkeep", "has_keep")) if p[key]]
    if p["has_last"]:
        ports.append(Port("tlast", scalar=True))
    ports += [Port(name, p[key]) for name, key in
              (("tid", "id_width"), ("tdest", "dest_width"), ("tuser", "user_width")) if p[key]]
    return tuple(ports)


def payload_settings(p):
    return {"TDATA_NUM_BYTES": p["data_bytes"], "TID_WIDTH": p["id_width"],
            "TDEST_WIDTH": p["dest_width"], "TUSER_WIDTH": p["user_width"],
            "HAS_TLAST": int(p["has_last"]), "HAS_TKEEP": int(p["has_keep"]),
            "HAS_TSTRB": int(p["has_strb"])}


@dataclass(frozen=True)
class StreamSpec:
    payload: tuple[Port, ...]
    settings: Mapping[str, object]
    model_parameters: Mapping[str, object]
    input_clock: str | None = "aclk"
    input_reset: str | None = "aresetn"
    output_clock: str | None = None
    output_reset: str | None = None
    output_period_ns: int = 10
    capacity: int = 2
    output_payload: tuple[Port, ...] | None = None
    masked_outputs: bool = False
    input_prefix: str = "s_axis"
    output_prefix: str = "m_axis"
    transfer_interval_cycles: int = 1
    drain_cycles: int = 64
    preserves_transfer_count: bool = True
    ignored_outputs: tuple[Port, ...] = ()
    tolerance_fields: tuple[tuple[int, bool], ...] = ()

    # The metadata checker sees clocks explicitly as ports, including both domains.
    clock = None

    @property
    def inputs(self):
        names = [name for name in (self.input_clock, self.input_reset) if name]
        names += [f"{self.input_prefix}_tvalid", f"{self.output_prefix}_tready"]
        names += [name for name in (self.output_clock, self.output_reset) if name]
        return (*tuple(Port(name, scalar=True) for name in names),
                *tuple(Port(f"{self.input_prefix}_{p.name}", p.width, p.scalar) for p in self.payload))

    @property
    def outputs(self):
        return (Port(f"{self.input_prefix}_tready", scalar=True),
                Port(f"{self.output_prefix}_tvalid", scalar=True),
                *tuple(Port(f"{self.output_prefix}_{p.name}", p.width, p.scalar)
                       for p in self.sink_payload), *self.ignored_outputs)

    @property
    def sink_payload(self):
        return self.payload if self.output_payload is None else self.output_payload

    @property
    def generated_ports(self):
        return tuple(port for port in self.payload if port.name not in {"tkeep", "tstrb", "tlast"})

    @property
    def width(self):
        return sum(port.width for port in self.payload)

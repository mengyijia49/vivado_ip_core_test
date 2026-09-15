from dataclasses import dataclass

from vivado_ip_test.plugins.common.cycle import Port


@dataclass(frozen=True)
class SwitchSpec:
    lane_payload: tuple[Port, ...]
    input_lane_count: int
    branch_count: int
    tag_field: str
    tag_bits: int
    routes: tuple[tuple[int, int], ...]
    parameters: dict
    settings: dict
    model_parameters: dict
    clock = None
    model_parameter_radices = {"C_M_AXIS_BASETDEST_ARRAY": 2, "C_M_AXIS_HIGHTDEST_ARRAY": 2,
                              "C_M_AXIS_CONNECTIVITY_ARRAY": 2, "C_AXIS_SIGNAL_SET": 2}

    @property
    def inputs(self):
        return (Port("aclk", scalar=True), Port("aresetn", scalar=True),
                Port("s_axis_tvalid", self.input_lane_count), Port("m_axis_tready", self.branch_count),
                *(Port(f"s_axis_{p.name}", p.width * self.input_lane_count) for p in self.lane_payload),
                *((Port("s_req_suppress", self.input_lane_count),) if self.branch_count == 1 else ()))

    @property
    def outputs(self):
        return (Port("s_axis_tready", self.input_lane_count), Port("m_axis_tvalid", self.branch_count),
                Port("s_decode_err", self.input_lane_count),
                *(Port(f"m_axis_{p.name}", p.width * self.branch_count) for p in self.lane_payload))

    @property
    def payload(self):
        return tuple(Port(f"s{lane:02d}_{p.name}", p.width, p.scalar)
                     for lane in range(self.input_lane_count) for p in self.lane_payload)

    @property
    def generated_ports(self):
        return tuple(Port(f"s{lane:02d}_{p.name}", p.width - (self.tag_bits if p.name == self.tag_field else 0))
                     for lane in range(self.input_lane_count) for p in self.lane_payload
                     if p.name in {"tdata", "tuser", "tid"})

    @property
    def route_bits(self):
        return max(1, (self.branch_count - 1).bit_length())

    @property
    def lane_output(self):
        return (Port("route", self.route_bits), *self.lane_payload)

    @property
    def sink_payload(self):
        return tuple(Port(f"s{lane:02d}_{p.name}", p.width, p.scalar)
                     for lane in range(self.input_lane_count) for p in self.lane_output)

    @property
    def width(self):
        return sum(p.width for p in self.payload)

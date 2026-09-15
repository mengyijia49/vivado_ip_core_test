from pathlib import Path
from string import Template


def render_testbench(spec, paths, count, max_gap, initial_stall):
    signals, mappings, assignments, captures, input_capture = [], [], [], [], []
    lane_width = sum(p.width for p in spec.lane_payload)
    for side, ports in (("s", spec.lane_payload), ("m", spec.sink_payload)):
        left = sum(p.width for p in ports) - 1
        for port in ports:
            scalar = side == "m" and port.scalar
            width = port.width * (spec.input_lane_count if side == "s" else 1)
            kind = "std_logic" if scalar else f"std_logic_vector({width - 1} downto 0)"
            signals.append(f"  signal {side}_{port.name} : {kind} := " +
                           ("'0';" if scalar else "(others => '0');"))
            mappings.append(f"{side}_axis_{port.name} => {side}_{port.name}")
            if side == "s":
                physical = f"(b + 1) * {port.width} - 1 downto b * {port.width}"
                packed = (f"(lanes - b - 1) * lane_width + {left} downto "
                          f"(lanes - b - 1) * lane_width + {left - port.width + 1}")
                assignments.append(f"              s_{port.name}({physical}) <= stimulus({packed});")
                input_capture.append(f"              accepted_value({packed}) := s_{port.name}({physical});")
            else:
                part = str(left) if scalar else f"{left} downto {left - port.width + 1}"
                captures.append(f"      actual({part}) := m_{port.name};")
            left -= port.width
    mappings.extend(("aclk => clk", "aresetn => resetn", "s_axis_tvalid => s_valid",
                     "s_axis_tready => s_ready", "m_axis_tvalid => m_valid", "m_axis_tready => m_ready"))
    values = {"signals": "\n".join(signals), "mappings": ",\n      ".join(mappings),
              "assignments": "\n".join(assignments), "captures": "\n".join(captures),
              "input_capture": "\n".join(input_capture), "count": count, "width": spec.width,
              "lanes": spec.input_lane_count, "lane_width": lane_width,
              "output_width": sum(p.width for p in spec.sink_payload), "initial_stall": initial_stall,
              "timeout_ns": 1000 + (initial_stall + (count + 1024) *
                                    (max_gap * 2 + 2 * spec.input_lane_count + 64)) * 10,
              **{name + "_path": str(path.resolve()).replace('"', '""') for name, path in paths.items()}}
    return Template((Path(__file__).parent / "templates/tb_combiner_selfcheck.vhd.tpl").read_text()).substitute(values)

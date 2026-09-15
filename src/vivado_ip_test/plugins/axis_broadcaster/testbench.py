from pathlib import Path
from string import Template


def render_testbench(spec, paths, count, max_gap, initial_stall):
    signals, mappings, assignments, captures, input_capture = [], [], [], [], []
    for side, ports in (("s", spec.payload), ("m", spec.branch_payload)):
        left = sum(p.width for p in ports) - 1
        for port in ports:
            scalar = side == "s" and port.scalar
            width = port.width * (1 if side == "s" else spec.branch_count)
            kind = "std_logic" if scalar else f"std_logic_vector({width - 1} downto 0)"
            signals.append(f"  signal {side}_{port.name} : {kind} := " +
                           ("'0';" if scalar else "(others => '0');"))
            mappings.append(f"{side}_axis_{port.name} => {side}_{port.name}")
            part = str(left) if port.scalar else f"{left} downto {left - port.width + 1}"
            if side == "s":
                assignments.append(f"      s_{port.name} <= stimulus({part});")
                input_capture.append(f"      accepted_value({part}) := s_{port.name};")
            else:
                source = "b" if port.scalar else f"(b + 1) * {port.width} - 1 downto b * {port.width}"
                captures.append(f"        actual(b)({part}) := m_{port.name}({source});")
            left -= port.width
    mappings.extend(("aclk => clk", "aresetn => resetn", "s_axis_tvalid => s_valid",
                     "s_axis_tready => s_ready", "m_axis_tvalid => m_valid", "m_axis_tready => m_ready"))
    values = {"signals": "\n".join(signals), "mappings": ",\n      ".join(mappings),
              "assignments": "\n".join(assignments), "captures": "\n".join(captures),
              "input_capture": "\n".join(input_capture), "count": count, "width": spec.width,
              "branches": spec.branch_count, "branch_width": sum(p.width for p in spec.branch_payload),
              "initial_stall": initial_stall,
              "timeout_ns": 1000 + (initial_stall + (count + 1024) *
                                    (max_gap + 2 * spec.branch_count + 64)) * 10,
              **{name + "_path": str(path.resolve()).replace('"', '""') for name, path in paths.items()}}
    return Template((Path(__file__).parent / "templates/tb_broadcaster_selfcheck.vhd.tpl").read_text()).substitute(values)

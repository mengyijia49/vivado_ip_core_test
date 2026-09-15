from pathlib import Path
from string import Template


def render_testbench(spec, paths, count, output_counts, max_gap, initial_stall):
    templates = Path(__file__).parent / "templates"
    signals, mappings, assignments, input_capture, captures = [], [], [], [], []
    lane_width = sum(p.width for p in spec.lane_payload)
    offsets = {}
    left = lane_width - 1
    for p in spec.lane_payload:
        part = f"{left} downto {left-p.width+1}"
        offsets[p.name] = (left, left-p.width+1)
        for side, lanes in (("s", spec.input_lane_count), ("m", spec.branch_count)):
            signals.append(f"  signal {side}_{p.name} : std_logic_vector({lanes*p.width-1} downto 0) := (others => '0');")
            mappings.append(f"{side}_axis_{p.name} => {side}_{p.name}")
        physical = f"(b+1)*{p.width}-1 downto b*{p.width}"
        assignments.append(f"      s_{p.name}({physical}) <= stimulus({part});")
        input_capture.append(f"      accepted_value({part}) := s_{p.name}({physical});")
        captures.append(f"        actual({part}) := m_{p.name}({physical});")
        left -= p.width
    mappings.extend(("aclk => clk", "aresetn => resetn", "s_axis_tvalid => s_valid",
        "s_axis_tready => s_ready", "m_axis_tvalid => m_valid", "m_axis_tready => m_ready", "s_decode_err => decode_err"))
    if spec.branch_count == 1:
        mappings.append("s_req_suppress => (others => '0')")
    values = {"signals": "\n".join(signals), "mappings": ",\n      ".join(mappings),
        "assignments": "\n".join(assignments), "input_capture": "\n".join(input_capture),
        "captures": "\n".join(captures), "lanes": spec.input_lane_count, "branches": spec.branch_count,
        "lane_width": lane_width, "route_bits": spec.route_bits, "count": count, "initial_stall": initial_stall,
        "timeout_ns": 1000 + (initial_stall + (count*spec.input_lane_count + 1024) *
            (max_gap + spec.parameters["arbitrate_cycles"] + 64)) * 10,
        **{key+"_path": str(path.resolve()).replace('"', '""') for key, path in paths.items()}}
    if spec.tag_bits:
        bottom = offsets[spec.tag_field][1]
        values["decode_source"] = f"lane := to_integer(unsigned(actual({bottom+spec.tag_bits-1} downto {bottom})));"
    else:
        values["decode_source"] = "lane := 0;"
    route_checks = []
    if "tdest" in offsets:
        high, low = offsets["tdest"]
        bits = high-low+1
        for branch, (base, top) in enumerate(spec.routes):
            route_checks.append(f"          when {branch} => assert unsigned(actual({high} downto {low})) >= "
                f"unsigned'(\"{base:0{bits}b}\") and unsigned(actual({high} downto {low})) <= "
                f"unsigned'(\"{top:0{bits}b}\")\n"
                "            report \"AXIS_SELF_CHECK_STATUS: FAIL wrong output route\" severity failure;")
    values["route_check"] = ("        case b is\n" + "\n".join(route_checks) +
                            "\n          when others => null;\n        end case;") if route_checks else ""
    drivers, declarations, dispatch, merge_outputs, merge_inputs, eof_checks = [], [], [], [], [], []
    for lane in range(spec.input_lane_count):
        drivers.append(Template((templates / "source_driver.vhd.tpl").read_text()).substitute(
            {**values, "lane": lane, "lane_input_path": values[f"input_{lane}_path"],
             "lane_gap_path": values[f"gaps_{lane}_path"], "lane_accepted_path": values[f"accepted_{lane}_path"],
             "lane_events_path": values[f"input_events_{lane}_path"]}))
        declarations.append(f"    file accepted_{lane} : text;")
        merge_inputs.append(f"    file_open(accepted_{lane}, \"{values[f'accepted_{lane}_path']}\", read_mode);\n"
            f"    while not endfile(accepted_{lane}) loop\n      readline(accepted_{lane}, row);\n"
            f"      writeline(accepted_file, row);\n    end loop;\n    file_close(accepted_{lane});")
        for branch in range(spec.branch_count):
            key = f"{lane}_{branch}"
            declarations += [f"    file expected_{key} : text open read_mode is \"{values[f'expected_{key}_path']}\";",
                             f"    file actual_{key} : text open write_mode is \"{values[f'actual_{key}_path']}\";"]
            dispatch.append(f"            when {lane*spec.branch_count+branch} =>\n"
                f"              write(output_row, complete_value);\n              writeline(actual_{key}, output_row);\n"
                f"              flush(actual_{key});\n              assert not endfile(expected_{key})\n"
                "                report \"AXIS_SELF_CHECK_STATUS: FAIL extra stream output\" severity failure;\n"
                f"              readline(expected_{key}, row);\n              read(row, wanted);")
            eof_checks.append(f"    assert endfile(expected_{key})\n"
                "      report \"AXIS_SELF_CHECK_STATUS: FAIL unread stream reference\" severity failure;")
            merge_outputs.append(f"    file_close(actual_{key});\n"
                f"    file_open(actual_{key}, \"{values[f'actual_{key}_path']}\", read_mode);\n"
                f"    while not endfile(actual_{key}) loop\n      readline(actual_{key}, row);\n"
                f"      writeline(actual_file, row);\n    end loop;\n    file_close(actual_{key});")
    values.update({"drivers": "\n".join(drivers), "files": "\n".join(declarations),
        "dispatch": "\n".join(dispatch), "merge_outputs": "\n".join(merge_outputs),
        "merge_inputs": "\n".join(merge_inputs), "eof_checks": "\n".join(eof_checks),
        "expected_counts": ",\n    ".join(f"{lane} => (" + ", ".join(
            f"{branch} => {value}" for branch, value in enumerate(row)) + ")"
            for lane, row in enumerate(output_counts))})
    return Template((templates / "tb_switch_selfcheck.vhd.tpl").read_text()).substitute(values)

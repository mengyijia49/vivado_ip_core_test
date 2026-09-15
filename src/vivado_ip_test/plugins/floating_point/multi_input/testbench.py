from pathlib import Path
from string import Template


def render_testbench(spec, paths, count, max_gap, initial_stall):
    signals, mappings, assignments, captures, accepted = [], [], [], [], []
    reads, files = [], []
    left = spec.width - 1
    for index, (lane, ports) in enumerate(spec.lanes):
        lane_assignments, lane_captures = [], []
        for port in ports:
            name = f'{lane}_{port.name}'
            kind = 'std_logic' if port.scalar else f'std_logic_vector({port.width - 1} downto 0)'
            initial = "'0'" if port.scalar else "(others => '0')"
            part = str(left) if port.scalar else f'{left} downto {left - port.width + 1}'
            signals.append(f'  signal {name} : {kind} := {initial};')
            mappings.append(f's_axis_{name} => {name}')
            lane_assignments.append(f'                {name} <= stimuli(b)({part});')
            lane_captures.append(f'              accepted_rows(acknowledged(b))({part}) := {name};')
            left -= port.width
        assignments.append(f'              when {index} =>\n' + '\n'.join(lane_assignments))
        accepted.append(f'            when {index} =>\n' + '\n'.join(lane_captures))
        mappings.extend((f's_axis_{lane}_tvalid => s_valid({index})', f's_axis_{lane}_tready => s_ready({index})'))
        for key in ('input_vectors', 'gaps'):
            path = str(paths[key].resolve()).replace('"', '""')
            files.append(f'    file {key}_{index} : text open read_mode is "{path}";')
        reads.append(f'''            when {index} =>
              assert not endfile(input_vectors_{index}) and not endfile(gaps_{index})
                report "AXIS_SELF_CHECK_STATUS: FAIL early input EOF" severity failure;
              readline(input_vectors_{index}, row);
              read(row, stimuli(b));
              readline(gaps_{index}, gap_row);''')
    left = sum(port.width for port in spec.sink_payload) - 1
    for port in spec.sink_payload:
        kind = 'std_logic' if port.scalar else f'std_logic_vector({port.width - 1} downto 0)'
        part = str(left) if port.scalar else f'{left} downto {left - port.width + 1}'
        signals.append(f'  signal result_{port.name} : {kind};')
        mappings.append(f'm_axis_result_{port.name} => result_{port.name}')
        captures.append(f'      actual({part}) := result_{port.name};')
        left -= port.width
    mappings.extend(('aclk => clk', 'aresetn => resetn', 'm_axis_result_tvalid => m_valid',
                     'm_axis_result_tready => m_ready'))
    final_files = '\n'.join(f'    assert endfile(input_vectors_{i}) and endfile(gaps_{i})\n'
        '      report "AXIS_SELF_CHECK_STATUS: FAIL extra input rows" severity failure;'
        for i in range(spec.input_lane_count))
    values = {'signals': '\n'.join(signals), 'mappings': ',\n      '.join(mappings),
        'assignments': '\n'.join(assignments), 'input_capture': '\n'.join(accepted),
        'captures': '\n'.join(captures), 'input_files': '\n'.join(files),
        'input_reads': '\n'.join(reads), 'final_files': final_files,
        'count': count, 'lanes': spec.input_lane_count, 'width': spec.width,
        'output_width': sum(port.width for port in spec.sink_payload), 'initial_stall': initial_stall,
        'timeout_ns': 1000 + (initial_stall + (count + 1024) * (
            max_gap * 2 + 96 + 2 * (spec.transfer_interval_cycles - 1))) * 10,
        **{name + '_path': str(path.resolve()).replace('"', '""') for name, path in paths.items()}}
    return Template((Path(__file__).parent / 'templates/tb_operands_selfcheck.vhd.tpl').read_text()).substitute(values)

from pathlib import Path
from string import Template


def _time_expression(nanoseconds):
    if type(nanoseconds) is not int or nanoseconds < 0:
        raise ValueError('Watchdog duration must be a nonnegative integer')
    if nanoseconds <= 2147483647:
        return f'{nanoseconds} ns'
    seconds, remainder = divmod(nanoseconds, 1000000000)
    if seconds > 2147483647:
        raise ValueError('Watchdog duration exceeds the supported VHDL literal range')
    return f'{seconds} sec + {remainder} ns'


def render_testbench(spec, paths, count, max_gap, actions):
    signals, mappings, drive_side, capture_side, audit_side = [], [], [], [], []
    for direction, ports in (("in", spec.side_inputs), ("out", spec.side_outputs)):
        for port in ports:
            kind = "std_logic" if port.scalar else f"std_logic_vector({port.width-1} downto 0)"
            initial = "'0'" if port.scalar else "(others => '0')"
            if spec.window and port.name == spec.window.control:
                initial = f"'{1-spec.window.active}'"
            signals.append(f"  signal p_{port.name} : {kind} := {initial};")
            mappings.append(f"{port.name} => p_{port.name}")
    command_parts = {}
    left = sum(p.width for p in spec.command_ports)-1
    for port in spec.command_ports:
        part = str(left) if port.scalar else f"{left} downto {left-port.width+1}"
        command_parts[port.name] = part
        if port in spec.side_inputs:
            drive_side.append(f"      p_{port.name} <= stimulus({part});")
            audit_side.append(f"      accepted({part}) := p_{port.name};")
        left -= port.width
    left = sum(p.width for p in spec.observation.outputs[2:])-1
    for port in spec.side_outputs:
        part = str(left) if port.scalar else f"{left} downto {left-port.width+1}"
        capture_side.append(f"      actual({part}) := p_{port.name};")
        left -= port.width
    pulse_checks, pulse_variables, pulse_reset = [], [], []
    for pulse in spec.pulses:
        name = pulse.count_port.name
        signals.append(f"  signal {name} : unsigned(31 downto 0) := (others => '0');")
        pulse_variables.append(f"    variable previous_{pulse.port} : boolean := false;")
        pulse_reset.append(f"        previous_{pulse.port} := false;")
        capture_side.append(f"      actual({left} downto {left-31}) := std_logic_vector({name});")
        left -= 32
        pulse_checks.append(f'''      assert p_{pulse.port} = '0' or p_{pulse.port} = '1'
        report "AXILITE_SELF_CHECK_STATUS: FAIL unknown pulse output {pulse.port}" severity failure;
      if p_{pulse.port} = '{pulse.active}' then
        assert not previous_{pulse.port}
          report "AXILITE_SELF_CHECK_STATUS: FAIL pulse wider than one clock {pulse.port}" severity failure;
        assert {name} /= x"FFFFFFFF"
          report "AXILITE_SELF_CHECK_STATUS: FAIL pulse counter overflow" severity failure;
        {name} <= {name}+1;
      end if;
      previous_{pulse.port} := p_{pulse.port} = '{pulse.active}';''')
    pulse_monitor = ''
    if pulse_checks:
        pulse_monitor = '''  pulse_monitor : process
''' + '\n'.join(pulse_variables) + '''
  begin
    loop
      wait until rising_edge(aclk);
      wait for 1 ps;
      if aresetn = '1' then
''' + '\n'.join(pulse_checks) + '''
      else
''' + '\n'.join(pulse_reset) + '''
      end if;
    end loop;
  end process;
'''
    window_driver = ''
    if spec.window:
        part = command_parts['run_cycles']
        window_driver = f'''        when 5 =>
          accepted({part}) := stimulus({part});
          assert unsigned(stimulus({part})) > 0
            report "AXILITE_SELF_CHECK_STATUS: FAIL empty clock window" severity failure;
          p_{spec.window.control} <= '{spec.window.active}';
          for i in 1 to to_integer(unsigned(stimulus({part}))) loop
            wait until falling_edge(aclk);
          end loop;
          p_{spec.window.control} <= '{1-spec.window.active}';'''
    for port in (*spec.inputs, *spec.outputs):
        if port not in (*spec.side_inputs, *spec.side_outputs):
            mappings.append(f"{port.name} => {port.name.removeprefix('s_axi_')}")
    return Template((Path(__file__).parent / "templates/tb_axilite_selfcheck.vhd.tpl").read_text()).substitute(
        side_signals="\n".join(signals), mappings=",\n      ".join(mappings),
        drive_side="\n".join(drive_side), capture_side="\n".join(capture_side), audit_side="\n".join(audit_side),
        window_driver=window_driver, pulse_monitor=pulse_monitor,
        input_width=sum(p.width for p in spec.command_ports), output_width=sum(p.width for p in spec.observation.outputs),
        side_width=sum(p.width for p in spec.observation.outputs[2:]), address_width=spec.address_width,
        action_part=command_parts["action"], address_part=command_parts["address"],
        data_part=command_parts["data"], strobe_part=command_parts["strobe"],
        count=count, writes=actions.get("write", 0), reads=actions.get("read", 0),
        settle_cycles=spec.settle_cycles, reset_cycles=spec.reset_cycles,
        timeout=_time_expression((count * (1600 + max_gap + spec.settle_cycles + spec.reset_cycles +
                                 ((1 << spec.window.width)-1 if spec.window else 0)) + 100) * 10),
        **{name+"_path": str(path.resolve()).replace('"', '""') for name, path in paths.items()})

library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_textio.all;
use std.textio.all;
use std.env.all;

entity tb_stream_selfcheck is
end entity;

architecture sim of tb_stream_selfcheck is
  constant count : positive := $count;
  constant lanes : positive := $lanes;
  constant lane_width : positive := $lane_width;
  type count_array is array (0 to lanes - 1) of natural;
  signal clk, resetn : std_logic := '0';
  signal s_valid, s_ready : std_logic_vector(lanes - 1 downto 0) := (others => '0');
  signal m_valid, m_ready : std_logic := '0';
  signal sent, offered, source_stalls : count_array := (others => 0);
  signal source_done : boolean := false;
$signals
begin
  clk <= not clk after 5 ns;
  resetn <= '1' after 200 ns;
  dut : entity work.dut_0
    port map (
      $mappings
    );

  source_driver : process
    file inputs : text open read_mode is "$input_vectors_path";
    file gaps : text open read_mode is "$gaps_path";
    file accepted : text open write_mode is "$accepted_input_path";
    variable row, gap_row, output_row : line;
    variable stimulus, accepted_value : std_logic_vector($width - 1 downto 0);
    variable issued, acknowledged : std_logic_vector(lanes - 1 downto 0);
    variable remaining, stalls : count_array := (others => 0);
    variable group_index : natural := 0;
  begin
    wait until resetn = '1';
    wait until falling_edge(clk);
    while not endfile(inputs) loop
      assert not endfile(gaps)
        report "AXIS_SELF_CHECK_STATUS: FAIL missing input gap" severity failure;
      readline(inputs, row);
      read(row, stimulus);
      readline(gaps, gap_row);
      for b in 0 to lanes - 1 loop
        read(gap_row, remaining(b));
      end loop;
      issued := (others => '0');
      acknowledged := (others => '0');
      accepted_value := (others => 'X');
      loop
        for b in 0 to lanes - 1 loop
          if issued(b) = '0' then
            if remaining(b) = 0 then
$assignments
              s_valid(b) <= '1';
              offered(b) <= group_index + 1;
              issued(b) := '1';
            else
              remaining(b) := remaining(b) - 1;
            end if;
          end if;
        end loop;
        wait until rising_edge(clk);
        for b in 0 to lanes - 1 loop
          if issued(b) = '1' and acknowledged(b) = '0' then
            assert s_ready(b) = '0' or s_ready(b) = '1'
              report "AXIS_SELF_CHECK_STATUS: FAIL unknown input ready lane=" & integer'image(b) severity failure;
            if s_ready(b) = '1' then
$input_capture
              acknowledged(b) := '1';
              sent(b) <= group_index + 1;
            else
              stalls(b) := stalls(b) + 1;
              source_stalls(b) <= stalls(b);
            end if;
          end if;
        end loop;
        wait until falling_edge(clk);
        for b in 0 to lanes - 1 loop
          if acknowledged(b) = '1' then
            s_valid(b) <= '0';
          end if;
        end loop;
        exit when (and acknowledged) = '1';
      end loop;
      write(output_row, accepted_value);
      writeline(accepted, output_row);
      flush(accepted);
      assert accepted_value = stimulus
        report "AXIS_SELF_CHECK_STATUS: FAIL source wiring mismatch" severity failure;
      group_index := group_index + 1;
    end loop;
    assert endfile(gaps) and group_index = count
      report "AXIS_SELF_CHECK_STATUS: FAIL input count" severity failure;
    source_done <= true;
    wait;
  end process;

  sink_driver : process
    file pattern : text open read_mode is "$ready_path";
    variable row : line;
    variable bit_value : std_logic;
  begin
    wait until resetn = '1';
    for i in 1 to $initial_stall loop
      wait until falling_edge(clk);
    end loop;
    loop
      if endfile(pattern) then
        file_close(pattern);
        file_open(pattern, "$ready_path", read_mode);
      end if;
      readline(pattern, row);
      read(row, bit_value);
      m_ready <= bit_value;
      wait until falling_edge(clk);
    end loop;
  end process;

  scoreboard : process
    file expected_file : text open read_mode is "$expected_output_path";
    file actual_file : text open write_mode is "$actual_output_path";
    file events : text open write_mode is "$protocol_events_path";
    file summary : text open write_mode is "$protocol_summary_path";
    variable row, output_row, event_row, summary_row : line;
    variable expected, actual, held : std_logic_vector($output_width - 1 downto 0);
    variable stalled : boolean := false;
    variable received, output_stalls, partial_input_cycles, drain_cycles, cycle : natural := 0;
  begin
    wait until resetn = '1';
    loop
      wait until rising_edge(clk);
      cycle := cycle + 1;
$captures
      if (or s_valid) = '1' and (and s_valid) = '0' then
        partial_input_cycles := partial_input_cycles + 1;
      end if;
      if m_valid /= '0' or (or s_valid) /= '0' or stalled then
        write(event_row, cycle);
        write(event_row, string'(" input_valid="));
        write(event_row, s_valid);
        write(event_row, string'(" input_ready="));
        write(event_row, s_ready);
        write(event_row, string'(" output_vr="));
        write(event_row, m_valid);
        write(event_row, m_ready);
        write(event_row, string'(" index="));
        write(event_row, received);
        if m_valid /= '0' then
          write(event_row, string'(" data="));
          write(event_row, actual);
        end if;
        writeline(events, event_row);
        flush(events);
      end if;
      assert m_valid = '0' or m_valid = '1'
        report "AXIS_SELF_CHECK_STATUS: FAIL unknown output valid" severity failure;
      if stalled then
        assert m_valid = '1' and not is_x(actual) and actual = held
          report "AXIS_SELF_CHECK_STATUS: FAIL output changed under backpressure" severity failure;
      end if;
      stalled := m_valid = '1' and m_ready = '0';
      if stalled then
        held := actual;
        output_stalls := output_stalls + 1;
      end if;
      if m_valid = '1' then
        for b in 0 to lanes - 1 loop
          assert received < offered(b)
            report "AXIS_SELF_CHECK_STATUS: FAIL output before all inputs offered lane=" & integer'image(b)
            severity failure;
        end loop;
      end if;
      if m_valid = '1' and m_ready = '1' then
        write(output_row, actual);
        writeline(actual_file, output_row);
        flush(actual_file);
        assert received < count and not endfile(expected_file)
          report "AXIS_SELF_CHECK_STATUS: FAIL extra output" severity failure;
        readline(expected_file, row);
        read(row, expected);
        assert not is_x(actual) and actual = expected
          report "AXIS_SELF_CHECK_STATUS: FAIL payload mismatch index=" & integer'image(received) severity failure;
        received := received + 1;
        wait for 0 ns;
        for b in 0 to lanes - 1 loop
          assert received <= sent(b)
            report "AXIS_SELF_CHECK_STATUS: FAIL output before all input handshakes lane=" & integer'image(b)
            severity failure;
        end loop;
      end if;
      if source_done and received = count then
        drain_cycles := drain_cycles + 1;
        exit when drain_cycles = 64;
      end if;
    end loop;
    assert endfile(expected_file)
      report "AXIS_SELF_CHECK_STATUS: FAIL unread reference" severity failure;
    write(summary_row, string'("output_accepted="));
    write(summary_row, received);
    writeline(summary, summary_row);
    write(summary_row, string'("output_stall_cycles="));
    write(summary_row, output_stalls);
    writeline(summary, summary_row);
    write(summary_row, string'("partial_input_cycles="));
    write(summary_row, partial_input_cycles);
    writeline(summary, summary_row);
    for b in 0 to lanes - 1 loop
      assert sent(b) = count and offered(b) = count
        report "AXIS_SELF_CHECK_STATUS: FAIL lane count" severity failure;
      write(summary_row, string'("lane="));
      write(summary_row, b);
      write(summary_row, string'(" accepted="));
      write(summary_row, sent(b));
      write(summary_row, string'(" input_stall_cycles="));
      write(summary_row, source_stalls(b));
      writeline(summary, summary_row);
    end loop;
    flush(summary);
    report "AXIS_SELF_CHECK_STATUS: PASS" severity note;
    finish;
    wait;
  end process;

  watchdog : process
  begin
    wait for $timeout_ns ns;
    assert false report "AXIS_SELF_CHECK_STATUS: FAIL watchdog timeout" severity failure;
    wait;
  end process;
end architecture;

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.std_logic_textio.all;
use std.textio.all;
use std.env.all;

entity tb_stream_selfcheck is
end entity;

architecture sim of tb_stream_selfcheck is
  constant lanes : positive := $lanes;
  constant branches : positive := $branches;
  constant count : positive := $count;
  constant lane_width : positive := $lane_width;
  constant route_bits : positive := $route_bits;
  type branch_counts is array (0 to branches-1) of natural;
  type stream_counts is array (0 to lanes-1) of branch_counts;
  type lane_counts is array (0 to lanes-1) of natural;
  type output_payloads is array (0 to branches-1) of std_logic_vector(lane_width-1 downto 0);
  constant expected_counts : stream_counts := (
    $expected_counts
  );
  signal clk, resetn : std_logic := '0';
  signal s_valid, s_ready, decode_err : std_logic_vector(lanes-1 downto 0) := (others => '0');
  signal m_valid, m_ready : std_logic_vector(branches-1 downto 0) := (others => '0');
  signal source_done : std_logic_vector(lanes-1 downto 0) := (others => '0');
  signal sent, offered : stream_counts := (others => (others => 0));
  signal source_stalls, source_route : lane_counts := (others => 0);
$signals
begin
  clk <= not clk after 5 ns;
  resetn <= '1' after 200 ns;
  dut : entity work.dut_0
    port map (
      $mappings
    );

$drivers

  sink_driver : process
    file pattern : text open read_mode is "$ready_path";
    variable row : line;
    variable bits : std_logic_vector(branches-1 downto 0);
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
      read(row, bits);
      m_ready <= bits;
      wait until falling_edge(clk);
    end loop;
  end process;

  scoreboard : process
    file actual_file : text open write_mode is "$actual_output_path";
    file accepted_file : text open write_mode is "$accepted_input_path";
    file events : text open write_mode is "$protocol_events_path";
    file summary : text open write_mode is "$protocol_summary_path";
$files
    variable row, output_row, event_row, summary_row : line;
    variable actual : std_logic_vector(lane_width-1 downto 0);
    variable complete_value, wanted : std_logic_vector(lane_width+route_bits-1 downto 0);
    variable held : output_payloads;
    variable stalled : std_logic_vector(branches-1 downto 0) := (others => '0');
    variable received : stream_counts := (others => (others => 0));
    variable output_stalls, contention_cycles : branch_counts := (others => 0);
    variable cycle, lane, total, drain_cycles, requests : natural := 0;
  begin
    wait until resetn = '1';
    loop
      wait until rising_edge(clk);
      cycle := cycle + 1;
      for b in 0 to branches-1 loop
$captures
        requests := 0;
        for s in 0 to lanes-1 loop
          if s_valid(s) = '1' and source_route(s) = b then
            requests := requests + 1;
          end if;
        end loop;
        if requests > 1 then
          contention_cycles(b) := contention_cycles(b) + 1;
        end if;
        if m_valid(b) /= '0' or stalled(b) = '1' then
          write(event_row, cycle);
          write(event_row, string'(" output="));
          write(event_row, b);
          write(event_row, string'(" vr="));
          write(event_row, m_valid(b));
          write(event_row, m_ready(b));
          write(event_row, string'(" input_valid="));
          write(event_row, s_valid);
          write(event_row, string'(" input_ready="));
          write(event_row, s_ready);
          write(event_row, string'(" data="));
          write(event_row, actual);
          writeline(events, event_row);
          flush(events);
        end if;
        assert m_valid(b) = '0' or m_valid(b) = '1'
          report "AXIS_SELF_CHECK_STATUS: FAIL unknown output valid" severity failure;
        if stalled(b) = '1' then
          assert m_valid(b) = '1' and not is_x(actual) and actual = held(b)
            report "AXIS_SELF_CHECK_STATUS: FAIL output changed under backpressure" severity failure;
        end if;
        stalled(b) := m_valid(b) and not m_ready(b);
        if stalled(b) = '1' then
          held(b) := actual;
          output_stalls(b) := output_stalls(b) + 1;
        end if;
        if m_valid(b) = '1' then
          assert not is_x(actual)
            report "AXIS_SELF_CHECK_STATUS: FAIL unknown valid payload" severity failure;
          $decode_source
          assert lane < lanes
            report "AXIS_SELF_CHECK_STATUS: FAIL invalid source tag" severity failure;
          assert received(lane)(b) < offered(lane)(b)
            report "AXIS_SELF_CHECK_STATUS: FAIL output before offered stream input" severity failure;
$route_check
          if m_ready(b) = '1' then
            complete_value := std_logic_vector(to_unsigned(b, route_bits)) & actual;
            case lane * branches + b is
$dispatch
              when others => assert false
                report "AXIS_SELF_CHECK_STATUS: FAIL stream dispatch" severity failure;
            end case;
            assert complete_value = wanted
              report "AXIS_SELF_CHECK_STATUS: FAIL payload or stream order mismatch source=" & integer'image(lane) &
                " output=" & integer'image(b) & " index=" & integer'image(received(lane)(b)) severity failure;
            received(lane)(b) := received(lane)(b) + 1;
            total := total + 1;
          end if;
        end if;
      end loop;
      wait for 0 ns;
      for s in 0 to lanes-1 loop
        for b in 0 to branches-1 loop
          assert received(s)(b) <= sent(s)(b)
            report "AXIS_SELF_CHECK_STATUS: FAIL output before input handshake" severity failure;
        end loop;
      end loop;
      if (and source_done) = '1' and total = count * lanes then
        drain_cycles := drain_cycles + 1;
        exit when drain_cycles = 64;
      end if;
    end loop;
    assert received = expected_counts and sent = expected_counts and offered = expected_counts
      report "AXIS_SELF_CHECK_STATUS: FAIL final stream count" severity failure;
$eof_checks
$merge_outputs
$merge_inputs
    flush(actual_file);
    flush(accepted_file);
    for s in 0 to lanes-1 loop
      write(summary_row, string'("source="));
      write(summary_row, s);
      write(summary_row, string'(" input_stall_cycles="));
      write(summary_row, source_stalls(s));
      writeline(summary, summary_row);
      for b in 0 to branches-1 loop
        write(summary_row, string'("source="));
        write(summary_row, s);
        write(summary_row, string'(" output="));
        write(summary_row, b);
        write(summary_row, string'(" accepted="));
        write(summary_row, sent(s)(b));
        write(summary_row, string'(" received="));
        write(summary_row, received(s)(b));
        writeline(summary, summary_row);
      end loop;
    end loop;
    for b in 0 to branches-1 loop
      write(summary_row, string'("output="));
      write(summary_row, b);
      write(summary_row, string'(" stall_cycles="));
      write(summary_row, output_stalls(b));
      write(summary_row, string'(" offered_contention_cycles="));
      write(summary_row, contention_cycles(b));
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

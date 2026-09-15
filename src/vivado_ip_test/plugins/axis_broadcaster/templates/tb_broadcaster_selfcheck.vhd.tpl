library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_textio.all;
use std.textio.all;
use std.env.all;

entity tb_stream_selfcheck is
end entity;

architecture sim of tb_stream_selfcheck is
  constant count : positive := $count;
  constant branches : positive := $branches;
  constant branch_width : positive := $branch_width;
  type payload_array is array (0 to branches - 1) of std_logic_vector(branch_width - 1 downto 0);
  type count_array is array (0 to branches - 1) of natural;
  signal clk, resetn : std_logic := '0';
  signal s_valid, s_ready : std_logic := '0';
  signal m_valid, m_ready : std_logic_vector(branches - 1 downto 0) := (others => '0');
  signal sent, offered, source_stalls : natural := 0;
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
    variable gap, accepted_count, stalls : natural := 0;
  begin
    wait until resetn = '1';
    wait until falling_edge(clk);
    while not endfile(inputs) loop
      assert not endfile(gaps)
        report "AXIS_SELF_CHECK_STATUS: FAIL missing input gap" severity failure;
      readline(inputs, row);
      read(row, stimulus);
      readline(gaps, gap_row);
      read(gap_row, gap);
      for i in 1 to gap loop
        wait until falling_edge(clk);
      end loop;
$assignments
      offered <= accepted_count + 1;
      s_valid <= '1';
      loop
        wait until rising_edge(clk);
        assert s_ready = '0' or s_ready = '1'
          report "AXIS_SELF_CHECK_STATUS: FAIL unknown input ready" severity failure;
        exit when s_ready = '1';
        stalls := stalls + 1;
        source_stalls <= stalls;
      end loop;
$input_capture
      write(output_row, accepted_value);
      writeline(accepted, output_row);
      flush(accepted);
      assert accepted_value = stimulus
        report "AXIS_SELF_CHECK_STATUS: FAIL source wiring mismatch" severity failure;
      accepted_count := accepted_count + 1;
      sent <= accepted_count;
      wait until falling_edge(clk);
      s_valid <= '0';
    end loop;
    assert endfile(gaps) and accepted_count = count
      report "AXIS_SELF_CHECK_STATUS: FAIL input count" severity failure;
    source_done <= true;
    wait;
  end process;

  sink_driver : process
    file pattern : text open read_mode is "$ready_path";
    variable row : line;
    variable bits : std_logic_vector(branches - 1 downto 0);
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
    file expected_file : text open read_mode is "$expected_output_path";
    file actual_file : text open write_mode is "$actual_output_path";
    file events : text open write_mode is "$protocol_events_path";
    file summary : text open write_mode is "$protocol_summary_path";
    variable row, output_row, event_row, summary_row : line;
    variable expected, collected : std_logic_vector(branches * branch_width - 1 downto 0);
    variable actual, held : payload_array;
    variable seen, stalled : std_logic_vector(branches - 1 downto 0) := (others => '0');
    variable received, stalls, early : count_array := (others => 0);
    variable completed, drain_cycles, cycle : natural := 0;
  begin
    collected := (others => 'X');
    wait until resetn = '1';
    assert not endfile(expected_file)
      report "AXIS_SELF_CHECK_STATUS: FAIL empty reference" severity failure;
    readline(expected_file, row);
    read(row, expected);
    loop
      wait until rising_edge(clk);
      cycle := cycle + 1;
      for b in 0 to branches - 1 loop
$captures
        if m_valid(b) /= '0' or stalled(b) = '1' then
          write(event_row, cycle);
          write(event_row, string'(" branch="));
          write(event_row, b);
          write(event_row, string'(" index="));
          write(event_row, received(b));
          write(event_row, string'(" vr="));
          write(event_row, m_valid(b));
          write(event_row, m_ready(b));
          write(event_row, string'(" data="));
          write(event_row, actual(b));
          writeline(events, event_row);
          flush(events);
        end if;
        assert m_valid(b) = '0' or m_valid(b) = '1'
          report "AXIS_SELF_CHECK_STATUS: FAIL unknown output valid branch=" & integer'image(b) severity failure;
        if stalled(b) = '1' then
          assert m_valid(b) = '1' and not is_x(actual(b)) and actual(b) = held(b)
            report "AXIS_SELF_CHECK_STATUS: FAIL output changed under backpressure branch=" & integer'image(b)
            severity failure;
        end if;
        stalled(b) := m_valid(b) and not m_ready(b);
        if stalled(b) = '1' then
          held(b) := actual(b);
          stalls(b) := stalls(b) + 1;
        end if;
        if m_valid(b) = '1' and m_ready(b) = '1' then
          assert received(b) < offered
            report "AXIS_SELF_CHECK_STATUS: FAIL output before offered input branch=" & integer'image(b)
            severity failure;
          assert seen(b) = '0' and completed < count
            report "AXIS_SELF_CHECK_STATUS: FAIL duplicate branch or extra output branch=" & integer'image(b)
            severity failure;
          collected((branches - b) * branch_width - 1 downto (branches - b - 1) * branch_width) := actual(b);
          if is_x(actual(b)) or actual(b) /=
             expected((branches - b) * branch_width - 1 downto (branches - b - 1) * branch_width) then
            write(output_row, collected);
            writeline(actual_file, output_row);
            flush(actual_file);
            assert false report "AXIS_SELF_CHECK_STATUS: FAIL payload mismatch branch=" & integer'image(b) &
              " index=" & integer'image(received(b)) severity failure;
          end if;
          seen(b) := '1';
          received(b) := received(b) + 1;
          if s_ready = '0' then
            early(b) := early(b) + 1;
          end if;
        end if;
      end loop;
      if (and seen) = '1' then
        write(output_row, collected);
        writeline(actual_file, output_row);
        flush(actual_file);
        completed := completed + 1;
        seen := (others => '0');
        collected := (others => 'X');
        if completed < count then
          assert not endfile(expected_file)
            report "AXIS_SELF_CHECK_STATUS: FAIL missing reference" severity failure;
          readline(expected_file, row);
          read(row, expected);
        end if;
      end if;
      if source_done and completed = count then
        drain_cycles := drain_cycles + 1;
        exit when drain_cycles = 64;
      end if;
    end loop;
    assert endfile(expected_file) and sent = count and offered = count
      report "AXIS_SELF_CHECK_STATUS: FAIL final count" severity failure;
    write(summary_row, string'("input_accepted="));
    write(summary_row, sent);
    writeline(summary, summary_row);
    write(summary_row, string'("complete_broadcasts="));
    write(summary_row, completed);
    writeline(summary, summary_row);
    write(summary_row, string'("input_stall_cycles="));
    write(summary_row, source_stalls);
    writeline(summary, summary_row);
    for b in 0 to branches - 1 loop
      assert received(b) = count
        report "AXIS_SELF_CHECK_STATUS: FAIL branch count" severity failure;
      write(summary_row, string'("branch="));
      write(summary_row, b);
      write(summary_row, string'(" accepted="));
      write(summary_row, received(b));
      write(summary_row, string'(" output_stall_cycles="));
      write(summary_row, stalls(b));
      write(summary_row, string'(" early_handshakes="));
      write(summary_row, early(b));
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

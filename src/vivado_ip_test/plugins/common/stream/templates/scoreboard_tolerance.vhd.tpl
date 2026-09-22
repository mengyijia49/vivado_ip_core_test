  scoreboard : process
    file expected_file : text open read_mode is "$expected_output_path";
    file tolerance_file : text open read_mode is "$output_tolerance_path";
    file actual_file : text open write_mode is "$actual_output_path";
    file events : text open write_mode is "$protocol_events_path";
    file summary : text open write_mode is "$protocol_summary_path";
    variable row, tolerance_row, output_row, event_row, summary_row : line;
    variable actual, expected, tolerance, held : std_logic_vector($output_width - 1 downto 0);
    variable sampled_valid, sampled_ready : std_logic;
    variable stalled : boolean := false;
    variable received, stalls, drain_cycles, cycle : natural := 0;
  begin
    wait until resetn = '1';
    loop
      wait until rising_edge(m_clk);
      cycle := cycle + 1;
      sampled_valid := m_valid;
      sampled_ready := m_ready;
$captures
      if sampled_valid /= '0' or stalled then
        write(event_row, cycle);
        write(event_row, string'(" "));
        write(event_row, sampled_valid);
        write(event_row, sampled_ready);
        write(event_row, string'(" "));
        write(event_row, actual);
        writeline(events, event_row);
        flush(events);
      end if;
      assert sampled_valid = '0' or sampled_valid = '1'
        report "AXIS_SELF_CHECK_STATUS: FAIL unknown output valid" severity failure;
      if stalled then
        assert sampled_valid = '1' and not is_x(actual) and actual = held
          report "AXIS_SELF_CHECK_STATUS: FAIL output changed under backpressure" severity failure;
      end if;
      stalled := sampled_valid = '1' and sampled_ready = '0';
      if stalled then
        held := actual;
        stalls := stalls + 1;
      end if;
      if sampled_valid = '1' and sampled_ready = '1' then
        write(output_row, actual);
        writeline(actual_file, output_row);
        flush(actual_file);
        assert not endfile(expected_file) and not endfile(tolerance_file)
          report "AXIS_SELF_CHECK_STATUS: FAIL extra output" severity failure;
        readline(expected_file, row);
        read(row, expected);
        readline(tolerance_file, tolerance_row);
        read(tolerance_row, tolerance);
        assert not is_x(actual) and
          $tolerance_comparison
          report "AXIS_SELF_CHECK_STATUS: FAIL payload mismatch index=" & integer'image(received) &
                 " expected=" & to_string(expected) & " actual=" & to_string(actual) severity failure;
        received := received + 1;
      end if;
      wait for 0 ns;
      assert received <= sent
        report "AXIS_SELF_CHECK_STATUS: FAIL output before accepted input" severity failure;
      if source_done and received = $output_count then
        drain_cycles := drain_cycles + 1;
        exit when drain_cycles = $drain_cycles;
      end if;
    end loop;
    assert endfile(expected_file) and endfile(tolerance_file) and sent = count
      report "AXIS_SELF_CHECK_STATUS: FAIL final count" severity failure;
    write(summary_row, string'("input_accepted="));
    write(summary_row, sent);
    writeline(summary, summary_row);
    write(summary_row, string'("output_accepted="));
    write(summary_row, received);
    writeline(summary, summary_row);
    write(summary_row, string'("input_stall_cycles="));
    write(summary_row, source_stalls);
    writeline(summary, summary_row);
    write(summary_row, string'("output_stall_cycles="));
    write(summary_row, stalls);
    writeline(summary, summary_row);
    flush(summary);
    report "AXIS_SELF_CHECK_STATUS: PASS" severity note;
    finish;
    wait;
  end process;

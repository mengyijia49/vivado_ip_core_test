  scoreboard : process
    file expected_file : text open read_mode is "$expected_output_path";
    file mask_file : text open read_mode is "$expected_mask_path";
    file causal_file : text open read_mode is "$required_inputs_path";
    file actual_file : text open write_mode is "$actual_output_path";
    file raw_file : text open write_mode is "$raw_output_path";
    file events : text open write_mode is "$protocol_events_path";
    file summary : text open write_mode is "$protocol_summary_path";
    variable row, output_row, event_row, summary_row : line;
    variable actual, held, qualified, held_mask : std_logic_vector($output_width - 1 downto 0);
    variable token : std_logic_vector($token_width - 1 downto 0);
    variable sampled_valid, sampled_ready : std_logic;
    variable stalled : boolean := false;
    variable received, beats, stalls, drain_cycles, cycle : natural := 0;

    procedure check_token(value : std_logic_vector) is
      variable expected, mask : std_logic_vector($token_width - 1 downto 0);
      variable required_count : natural;
      variable line_value : line;
    begin
      write(line_value, value);
      writeline(actual_file, line_value);
      flush(actual_file);
      assert not endfile(expected_file) and not endfile(mask_file) and not endfile(causal_file)
        report "AXIS_SELF_CHECK_STATUS: FAIL extra byte or packet boundary" severity failure;
      readline(expected_file, line_value); read(line_value, expected);
      readline(mask_file, line_value); read(line_value, mask);
      readline(causal_file, line_value); read(line_value, required_count);
      assert sent >= required_count
        report "AXIS_SELF_CHECK_STATUS: FAIL output before accepted input" severity failure;
      assert not is_x(value and mask) and (value and mask) = (expected and mask)
        report "AXIS_SELF_CHECK_STATUS: FAIL token mismatch index=" & integer'image(received) &
               " expected=" & to_string(expected) & " actual=" & to_string(value) severity failure;
      received := received + 1;
    end procedure;
  begin
    wait until resetn = '1';
    loop
      wait until rising_edge(m_clk);
      cycle := cycle + 1;
      sampled_valid := m_valid;
      sampled_ready := m_ready;
$captures
      wait for 0 ns;
      if sampled_valid /= '0' or stalled then
        write(event_row, cycle); write(event_row, string'(" "));
        write(event_row, sampled_valid); write(event_row, sampled_ready);
        write(event_row, string'(" ")); write(event_row, actual);
        writeline(events, event_row); flush(events);
      end if;
      assert sampled_valid = '0' or sampled_valid = '1'
        report "AXIS_SELF_CHECK_STATUS: FAIL unknown output valid" severity failure;
      if stalled then
        assert sampled_valid = '1' and not is_x(actual and held_mask) and
               (actual and held_mask) = (held and held_mask)
          report "AXIS_SELF_CHECK_STATUS: FAIL output changed under backpressure" severity failure;
      end if;
      stalled := sampled_valid = '1' and sampled_ready = '0';
      if sampled_valid = '1' then
        qualified := (others => '1');
$qualification
        assert not is_x(actual and qualified)
          report "AXIS_SELF_CHECK_STATUS: FAIL unknown qualified output" severity failure;
        if stalled then
          held := actual;
          held_mask := qualified;
          stalls := stalls + 1;
        end if;
        if sampled_ready = '1' then
          write(output_row, actual); writeline(raw_file, output_row); flush(raw_file);
          beats := beats + 1;
$token_extraction
        end if;
      end if;
      if source_done and received = $token_count then
        drain_cycles := drain_cycles + 1;
        exit when drain_cycles = 64;
      end if;
    end loop;
    assert endfile(expected_file) and endfile(mask_file) and endfile(causal_file) and sent = count
      report "AXIS_SELF_CHECK_STATUS: FAIL final count" severity failure;
    write(summary_row, string'("input_accepted=")); write(summary_row, sent); writeline(summary, summary_row);
    write(summary_row, string'("output_accepted=")); write(summary_row, beats); writeline(summary, summary_row);
    write(summary_row, string'("checked_tokens=")); write(summary_row, received); writeline(summary, summary_row);
    write(summary_row, string'("input_stall_cycles=")); write(summary_row, source_stalls); writeline(summary, summary_row);
    write(summary_row, string'("output_stall_cycles=")); write(summary_row, stalls); writeline(summary, summary_row);
    flush(summary);
    report "AXIS_SELF_CHECK_STATUS: PASS" severity note;
    finish;
    wait;
  end process;

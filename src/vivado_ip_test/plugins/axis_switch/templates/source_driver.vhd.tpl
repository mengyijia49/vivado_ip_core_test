  source_$lane : process
    constant b : natural := $lane;
    file inputs : text open read_mode is "$lane_input_path";
    file gaps : text open read_mode is "$lane_gap_path";
    file accepted : text open write_mode is "$lane_accepted_path";
    file events : text open write_mode is "$lane_events_path";
    variable row, gap_row, output_row, event_row : line;
    variable stimulus : std_logic_vector(lane_width + route_bits - 1 downto 0);
    variable accepted_value : std_logic_vector(lane_width - 1 downto 0);
    variable accepted_counts, offered_counts : branch_counts := (others => 0);
    variable gap, destination, transferred, stalls : natural := 0;
  begin
    wait until resetn = '1';
    wait until falling_edge(clk);
    while not endfile(inputs) loop
      assert not endfile(gaps)
        report "AXIS_SELF_CHECK_STATUS: FAIL missing source gap" severity failure;
      readline(inputs, row);
      read(row, stimulus);
      readline(gaps, gap_row);
      read(gap_row, gap);
      for i in 1 to gap loop
        wait until falling_edge(clk);
      end loop;
      destination := to_integer(unsigned(stimulus(lane_width + route_bits - 1 downto lane_width)));
      assert destination < branches
        report "AXIS_SELF_CHECK_STATUS: FAIL invalid planned destination" severity failure;
$assignments
      offered_counts(destination) := offered_counts(destination) + 1;
      offered(b) <= offered_counts;
      source_route(b) <= destination;
      s_valid(b) <= '1';
      loop
        wait until rising_edge(clk);
        write(event_row, now);
        write(event_row, string'(" index="));
        write(event_row, transferred);
        write(event_row, string'(" route="));
        write(event_row, destination);
        write(event_row, string'(" ready="));
        write(event_row, s_ready(b));
        write(event_row, string'(" decode_error="));
        write(event_row, decode_err(b));
        writeline(events, event_row);
        flush(events);
        assert s_ready(b) = '0' or s_ready(b) = '1'
          report "AXIS_SELF_CHECK_STATUS: FAIL unknown input ready" severity failure;
        assert decode_err(b) = '0'
          report "AXIS_SELF_CHECK_STATUS: FAIL decode error for legal input" severity failure;
        exit when s_ready(b) = '1';
        stalls := stalls + 1;
        source_stalls(b) <= stalls;
      end loop;
$input_capture
      write(output_row, accepted_value);
      writeline(accepted, output_row);
      flush(accepted);
      assert accepted_value = stimulus(lane_width - 1 downto 0)
        report "AXIS_SELF_CHECK_STATUS: FAIL source wiring mismatch" severity failure;
      accepted_counts(destination) := accepted_counts(destination) + 1;
      sent(b) <= accepted_counts;
      transferred := transferred + 1;
      wait until falling_edge(clk);
      s_valid(b) <= '0';
    end loop;
    assert endfile(gaps) and transferred = count
      report "AXIS_SELF_CHECK_STATUS: FAIL input count" severity failure;
    file_close(accepted);
    source_done(b) <= '1';
    wait;
  end process;

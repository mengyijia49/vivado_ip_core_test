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
  type count_array is array (0 to lanes - 1) of natural;
  type bool_array is array (0 to lanes - 1) of boolean;
  type word_array is array (natural range <>) of std_logic_vector($width - 1 downto 0);
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
$input_files
    file audit_inputs : text open read_mode is "$input_vectors_path";
    file accepted : text open write_mode is "$accepted_input_path";
    variable row, gap_row, output_row : line;
    variable stimuli : word_array(0 to lanes - 1);
    variable accepted_rows : word_array(0 to count - 1) := (others => (others => 'X'));
    variable wanted : std_logic_vector($width - 1 downto 0);
    variable loaded, issued : bool_array := (others => false);
    variable remaining, acknowledged, stalls : count_array := (others => 0);
    variable gap, assembled, lowest : natural := 0;
  begin
    wait until resetn = '1';
    loop
      wait until falling_edge(clk);
      for b in 0 to lanes - 1 loop
        if not issued(b) then
          s_valid(b) <= '0';
        end if;
        if not loaded(b) and acknowledged(b) < count then
          case b is
$input_reads
            when others => null;
          end case;
          for j in 0 to lanes - 1 loop
            read(gap_row, gap);
            if j = b then
              remaining(b) := gap;
            end if;
          end loop;
          loaded(b) := true;
        end if;
        if loaded(b) and not issued(b) then
          if remaining(b) = 0 then
            case b is
$assignments
              when others => null;
            end case;
            s_valid(b) <= '1';
            offered(b) <= acknowledged(b) + 1;
            issued(b) := true;
          else
            remaining(b) := remaining(b) - 1;
          end if;
        end if;
      end loop;
      wait until rising_edge(clk);
      for b in 0 to lanes - 1 loop
        if issued(b) then
          assert s_ready(b) = '0' or s_ready(b) = '1'
            report "AXIS_SELF_CHECK_STATUS: FAIL unknown input ready lane=" & integer'image(b) severity failure;
          if s_ready(b) = '1' then
            case b is
$input_capture
              when others => null;
            end case;
            acknowledged(b) := acknowledged(b) + 1;
            sent(b) <= acknowledged(b);
            issued(b) := false;
            loaded(b) := false;
          else
            stalls(b) := stalls(b) + 1;
            source_stalls(b) <= stalls(b);
          end if;
        end if;
      end loop;
      lowest := acknowledged(0);
      for b in 1 to lanes - 1 loop
        if acknowledged(b) < lowest then
          lowest := acknowledged(b);
        end if;
      end loop;
      while assembled < lowest loop
        assert not endfile(audit_inputs)
          report "AXIS_SELF_CHECK_STATUS: FAIL accepted input count" severity failure;
        readline(audit_inputs, row);
        read(row, wanted);
        write(output_row, accepted_rows(assembled));
        writeline(accepted, output_row);
        flush(accepted);
        assert accepted_rows(assembled) = wanted
          report "AXIS_SELF_CHECK_STATUS: FAIL source wiring mismatch" severity failure;
        assembled := assembled + 1;
      end loop;
      exit when assembled = count;
    end loop;
    wait until falling_edge(clk);
    s_valid <= (others => '0');
$final_files
    assert endfile(audit_inputs)
      report "AXIS_SELF_CHECK_STATUS: FAIL unread source audit" severity failure;
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
    variable lowest, highest, max_accepted_skew : natural := 0;
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
      if m_valid = '1' and m_ready = '1' then
        write(output_row, actual);
        writeline(actual_file, output_row);
        flush(actual_file);
        assert received < count and not endfile(expected_file)
          report "AXIS_SELF_CHECK_STATUS: FAIL extra output" severity failure;
        for b in 0 to lanes - 1 loop
          assert received < offered(b)
            report "AXIS_SELF_CHECK_STATUS: FAIL output before operand offered" severity failure;
        end loop;
        readline(expected_file, row);
        read(row, expected);
        assert not is_x(actual) and actual = expected
          report "AXIS_SELF_CHECK_STATUS: FAIL payload mismatch index=" & integer'image(received) &
                 " expected=" & to_string(expected) & " actual=" & to_string(actual) severity failure;
        received := received + 1;
      end if;
      wait for 0 ns;
      lowest := sent(0);
      highest := sent(0);
      for b in 0 to lanes - 1 loop
        assert received <= sent(b)
          report "AXIS_SELF_CHECK_STATUS: FAIL output before operand handshake" severity failure;
        if sent(b) < lowest then lowest := sent(b); end if;
        if sent(b) > highest then highest := sent(b); end if;
      end loop;
      if highest - lowest > max_accepted_skew then
        max_accepted_skew := highest - lowest;
      end if;
      if source_done and received = count then
        drain_cycles := drain_cycles + 1;
        exit when drain_cycles = 128;
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
    write(summary_row, string'("max_accepted_operand_skew="));
    write(summary_row, max_accepted_skew);
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

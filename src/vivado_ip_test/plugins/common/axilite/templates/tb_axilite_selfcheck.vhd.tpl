library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.std_logic_textio.all;
use std.textio.all;
use std.env.all;

entity tb_axilite_selfcheck is
end entity;

architecture sim of tb_axilite_selfcheck is
  constant command_count : positive := $count;
  constant input_width : positive := $input_width;
  constant output_width : positive := $output_width;
  constant side_width : natural := $side_width;
  signal aclk, aresetn : std_logic := '0';
  signal awaddr, araddr : std_logic_vector($address_width-1 downto 0) := (others => '0');
  signal wdata, rdata : std_logic_vector(31 downto 0) := (others => '0');
  signal active_read_mask : std_logic_vector(31 downto 0) := (others => '1');
  signal wstrb : std_logic_vector(3 downto 0) := (others => '0');
  signal bresp, rresp : std_logic_vector(1 downto 0) := (others => '0');
  signal awvalid, awready, wvalid, wready, bvalid, bready : std_logic := '0';
  signal arvalid, arready, rvalid, rready : std_logic := '0';
  signal completed_writes, completed_reads : natural := 0;
  signal b_stall_cycles, r_stall_cycles, request_wait_cycles : natural := 0;
  signal operation_index : natural := 0;
$side_signals
$extra_declarations
begin
  aclk <= not aclk after 5 ns;
$loopback_assignments
$extra_statements
  dut : entity work.dut_0
    port map (
      $mappings
    );

  driver : process
    file inputs_file : text open read_mode is "$input_vectors_path";
    file expected_file : text open read_mode is "$expected_output_path";
    file masks_file : text open read_mode is "$expected_mask_path";
    file timing_file : text open read_mode is "$timing_path";
    file actual_file : text open write_mode is "$actual_output_path";
    file accepted_file : text open write_mode is "$accepted_input_path";
    file mismatches : text open write_mode is "$mismatches_path";
    file summary : text open write_mode is "$protocol_summary_path";
    variable row, output_row : line;
    variable stimulus, accepted : std_logic_vector(input_width-1 downto 0);
    variable wanted, mask, actual : std_logic_vector(output_width-1 downto 0);
    variable response_sample : std_logic_vector(1 downto 0);
    variable read_sample : std_logic_vector(31 downto 0);
    variable action, gap, hold_cycles, cycles : natural;
    variable got_aw, got_w : boolean;
    variable mismatch_count : natural := 0;
  begin
    for i in 1 to $reset_cycles loop
      wait until falling_edge(aclk);
    end loop;
    aresetn <= '1';
    for index in 0 to command_count-1 loop
      operation_index <= index;
      assert not endfile(inputs_file) and not endfile(expected_file) and not endfile(masks_file)
             and not endfile(timing_file)
        report "AXILITE_SELF_CHECK_STATUS: FAIL missing operation file row" severity failure;
      readline(inputs_file, row); read(row, stimulus);
      readline(expected_file, row); read(row, wanted);
      readline(masks_file, row); read(row, mask);
      readline(timing_file, row); read(row, gap); read(row, hold_cycles);
      assert not is_x(stimulus) and not is_x(wanted) and not is_x(mask)
        report "AXILITE_SELF_CHECK_STATUS: FAIL invalid operation file row" severity failure;
      for i in 1 to gap+1 loop
        wait until falling_edge(aclk);
      end loop;
      action := to_integer(unsigned(stimulus($action_part)));
      accepted := (others => '0');
      accepted($action_part) := stimulus($action_part);
      response_sample := (others => '0');
      read_sample := (others => '0');
$drive_side
      case action is
        when 0 =>
          awaddr <= stimulus($address_part);
          wdata <= stimulus($data_part);
          wstrb <= stimulus($strobe_part);
          awvalid <= '1'; wvalid <= '1'; bready <= '0';
          got_aw := false; got_w := false; cycles := 0;
          loop
            wait until rising_edge(aclk);
            cycles := cycles+1;
            assert cycles < 512
              report "AXILITE_SELF_CHECK_STATUS: FAIL write request timeout" severity failure;
            if awvalid = '1' and awready = '1' then
              assert not got_aw report "AXILITE_SELF_CHECK_STATUS: FAIL repeated write address" severity failure;
              accepted($address_part) := awaddr;
              got_aw := true;
            end if;
            if wvalid = '1' and wready = '1' then
              assert not got_w report "AXILITE_SELF_CHECK_STATUS: FAIL repeated write data" severity failure;
              accepted($data_part) := wdata;
              accepted($strobe_part) := wstrb;
              got_w := true;
            end if;
            wait until falling_edge(aclk);
            if got_aw then awvalid <= '0'; end if;
            if got_w then wvalid <= '0'; end if;
            exit when got_aw and got_w;
          end loop;
          cycles := 0;
          loop
            wait until rising_edge(aclk);
            cycles := cycles+1;
            assert cycles < 512 report "AXILITE_SELF_CHECK_STATUS: FAIL write response timeout" severity failure;
            exit when bvalid = '1';
          end loop;
          for i in 1 to hold_cycles loop
            wait until rising_edge(aclk);
          end loop;
          wait until falling_edge(aclk);
          bready <= '1';
          wait until rising_edge(aclk);
          assert bvalid = '1' report "AXILITE_SELF_CHECK_STATUS: FAIL write response vanished" severity failure;
          response_sample := bresp;
          wait until falling_edge(aclk);
          bready <= '0';
        when 1 =>
          active_read_mask <= mask(output_width-3 downto side_width);
          araddr <= stimulus($address_part);
          arvalid <= '1'; rready <= '0'; cycles := 0;
          loop
            wait until rising_edge(aclk);
            cycles := cycles+1;
            assert cycles < 512 report "AXILITE_SELF_CHECK_STATUS: FAIL read request timeout" severity failure;
            exit when arready = '1';
          end loop;
          accepted($address_part) := araddr;
          wait until falling_edge(aclk);
          arvalid <= '0'; cycles := 0;
          loop
            wait until rising_edge(aclk);
            cycles := cycles+1;
            assert cycles < 512 report "AXILITE_SELF_CHECK_STATUS: FAIL read response timeout" severity failure;
            exit when rvalid = '1';
          end loop;
          for i in 1 to hold_cycles loop
            wait until rising_edge(aclk);
          end loop;
          wait until falling_edge(aclk);
          rready <= '1';
          wait until rising_edge(aclk);
          assert rvalid = '1' report "AXILITE_SELF_CHECK_STATUS: FAIL read response vanished" severity failure;
          response_sample := rresp; read_sample := rdata;
          wait until falling_edge(aclk);
          rready <= '0';
        when 3 =>
          aresetn <= '0';
          for i in 1 to $reset_cycles loop
            wait until falling_edge(aclk);
          end loop;
          aresetn <= '1';
        when 2 | 4 => null;
$window_driver
        when others => assert false
          report "AXILITE_SELF_CHECK_STATUS: FAIL invalid action" severity failure;
      end case;
      for i in 1 to $settle_cycles loop
        wait until falling_edge(aclk);
      end loop;
      actual := (others => '0');
      actual(output_width-1 downto output_width-2) := response_sample;
      actual(output_width-3 downto side_width) := read_sample;
$capture_side
$audit_side
      write(output_row, accepted); writeline(accepted_file, output_row); flush(accepted_file);
      write(output_row, actual); writeline(actual_file, output_row); flush(actual_file);
      assert accepted = stimulus
        report "AXILITE_SELF_CHECK_STATUS: FAIL sampled request differs from planned input operation=" & integer'image(index) severity failure;
      if is_x(actual and mask) or (actual and mask) /= (wanted and mask) then
        mismatch_count := mismatch_count+1;
        write(output_row, index); write(output_row, string'(" ")); write(output_row, wanted);
        write(output_row, string'(" ")); write(output_row, actual);
        write(output_row, string'(" ")); write(output_row, mask);
        writeline(mismatches, output_row); flush(mismatches);
        if mismatch_count <= 20 then
          report "AXILITE_MISMATCH operation=" & integer'image(index) severity warning;
        end if;
      end if;
    end loop;
    assert endfile(inputs_file) and endfile(expected_file) and endfile(masks_file) and endfile(timing_file)
      report "AXILITE_SELF_CHECK_STATUS: FAIL extra operation rows" severity failure;
    for i in 1 to 64 loop
      wait until falling_edge(aclk);
    end loop;
    assert completed_writes = $writes and completed_reads = $reads
      report "AXILITE_SELF_CHECK_STATUS: FAIL response count" severity failure;
    write(row, string'("completed_writes=")); write(row, completed_writes); writeline(summary, row);
    write(row, string'("completed_reads=")); write(row, completed_reads); writeline(summary, row);
    write(row, string'("write_response_stall_cycles=")); write(row, b_stall_cycles); writeline(summary, row);
    write(row, string'("read_response_stall_cycles=")); write(row, r_stall_cycles); writeline(summary, row);
    write(row, string'("request_wait_cycles=")); write(row, request_wait_cycles); writeline(summary, row);
    write(row, string'("numeric_mismatches=")); write(row, mismatch_count); writeline(summary, row);
    flush(summary);
    assert mismatch_count = 0
      report "AXILITE_SELF_CHECK_STATUS: FAIL register or pin mismatches=" & integer'image(mismatch_count) severity failure;
    report "AXILITE_SELF_CHECK_STATUS: PASS" severity note;
    finish;
    wait;
  end process;

  protocol_monitor : process
    file events : text open write_mode is "$protocol_events_path";
    variable row : line;
    variable cycles, aw_count, w_count, b_count, ar_count, r_count : natural := 0;
    variable held_b, held_r : boolean := false;
    variable previous_bresp, previous_rresp : std_logic_vector(1 downto 0);
    variable previous_rdata : std_logic_vector(31 downto 0);
  begin
    loop
      wait until rising_edge(aclk);
      cycles := cycles+1;
      if aresetn = '0' then
        aw_count := 0; w_count := 0; b_count := 0; ar_count := 0; r_count := 0;
        held_b := false; held_r := false;
        wait for 1 ps;
        assert bvalid = '0' and rvalid = '0'
          report "AXILITE_SELF_CHECK_STATUS: FAIL response valid during reset" severity failure;
      else
        if awvalid = '1' or wvalid = '1' or arvalid = '1' or bvalid /= '0' or rvalid /= '0' then
          write(row, cycles); write(row, string'(" operation=")); write(row, operation_index);
          write(row, string'(" aw=")); write(row, awvalid); write(row, awready);
          write(row, string'(" addr=")); write(row, awaddr);
          write(row, string'(" w=")); write(row, wvalid); write(row, wready);
          write(row, string'(" data=")); write(row, wdata); write(row, string'(" strb=")); write(row, wstrb);
          write(row, string'(" b=")); write(row, bvalid); write(row, bready);
          write(row, string'(" resp=")); write(row, bresp);
          write(row, string'(" ar=")); write(row, arvalid); write(row, arready);
          write(row, string'(" addr=")); write(row, araddr);
          write(row, string'(" r=")); write(row, rvalid); write(row, rready);
          write(row, string'(" data=")); write(row, rdata); write(row, string'(" resp=")); write(row, rresp);
          writeline(events, row); flush(events);
        end if;
        assert (bvalid = '0' or bvalid = '1') and (rvalid = '0' or rvalid = '1')
          report "AXILITE_SELF_CHECK_STATUS: FAIL unknown response valid" severity failure;
        assert (awvalid = '0' or awready = '0' or awready = '1') and
               (wvalid = '0' or wready = '0' or wready = '1') and
               (arvalid = '0' or arready = '0' or arready = '1')
          report "AXILITE_SELF_CHECK_STATUS: FAIL unknown request ready" severity failure;
        if (awvalid = '1' and awready = '0') or (wvalid = '1' and wready = '0') or
           (arvalid = '1' and arready = '0') then
          request_wait_cycles <= request_wait_cycles+1;
        end if;
        if held_b then
          assert bvalid = '1' and bresp = previous_bresp
            report "AXILITE_SELF_CHECK_STATUS: FAIL write response changed under backpressure" severity failure;
        end if;
        if held_r then
          assert rvalid = '1' and rresp = previous_rresp and rdata = previous_rdata
            report "AXILITE_SELF_CHECK_STATUS: FAIL read response changed under backpressure" severity failure;
        end if;
        held_b := bvalid = '1' and bready = '0';
        held_r := rvalid = '1' and rready = '0';
        if held_b then
          previous_bresp := bresp; b_stall_cycles <= b_stall_cycles+1;
        end if;
        if held_r then
          previous_rresp := rresp; previous_rdata := rdata; r_stall_cycles <= r_stall_cycles+1;
        end if;
        if bvalid = '1' then
          assert b_count < aw_count and b_count < w_count
            report "AXILITE_SELF_CHECK_STATUS: FAIL write response without both requests" severity failure;
          assert not is_x(bresp) report "AXILITE_SELF_CHECK_STATUS: FAIL unknown write response" severity failure;
          if bready = '1' then
            b_count := b_count+1; completed_writes <= completed_writes+1;
          end if;
        end if;
        if rvalid = '1' then
          assert r_count < ar_count
            report "AXILITE_SELF_CHECK_STATUS: FAIL read response without request" severity failure;
          assert not is_x(rdata and active_read_mask) and not is_x(rresp)
            report "AXILITE_SELF_CHECK_STATUS: FAIL unknown read response" severity failure;
          if rready = '1' then
            r_count := r_count+1; completed_reads <= completed_reads+1;
          end if;
        end if;
        -- A response needs a request accepted on an earlier edge, not this edge.
        if awvalid = '1' and awready = '1' then aw_count := aw_count+1; end if;
        if wvalid = '1' and wready = '1' then w_count := w_count+1; end if;
        if arvalid = '1' and arready = '1' then ar_count := ar_count+1; end if;
      end if;
    end loop;
  end process;

$pulse_monitor
  watchdog : process
  begin
    wait for $timeout;
    assert false report "AXILITE_SELF_CHECK_STATUS: FAIL watchdog timeout" severity failure;
    wait;
  end process;
end architecture;

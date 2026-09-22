library ieee;
use ieee.std_logic_1164.all;
use std.textio.all;
use std.env.all;

entity tb_clocking_wizard_selfcheck is
end entity;

architecture test of tb_clocking_wizard_selfcheck is
  constant C_INPUT_HALF_PERIOD : time := ${input_half_period_ps} ps;
  constant C_OUTPUT_PERIOD : time := ${output_period_ps} ps;
  constant C_OUTPUT_HIGH : time := ${output_high_ps} ps;
  constant C_TOLERANCE : time := 5 ps;
  signal clk_in1 : std_logic := '0';
  signal clk_out1 : std_logic;
  signal locked : std_logic;
  signal p_reset : std_logic := ${reset_initial};
begin
  clk_in1 <= not clk_in1 after C_INPUT_HALF_PERIOD;

  dut : entity work.dut_0
    port map (
      clk_in1 => clk_in1,
      clk_out1 => clk_out1,
      locked => locked,
      ${reset_name} => p_reset
    );

  stimulus : process
    file actual_file : text open write_mode is "${actual_path}";
    variable output_line : line;
    variable previous_edge : time;
    variable measured : time;

    procedure record_event(constant value : in string) is
    begin
      write(output_line, value);
      writeline(actual_file, output_line);
    end procedure;

    procedure measure_output(constant event_name : in string) is
    begin
      wait until rising_edge(clk_out1) for 2 * C_OUTPUT_PERIOD;
      assert rising_edge(clk_out1)
        report "CLOCK_WIZARD_SELF_CHECK_STATUS: FAIL missing output edge" severity failure;
      previous_edge := now;
      for index in 1 to 16 loop
        wait until rising_edge(clk_out1) for 2 * C_OUTPUT_PERIOD;
        assert rising_edge(clk_out1)
          report "CLOCK_WIZARD_SELF_CHECK_STATUS: FAIL output clock stopped" severity failure;
        measured := now - previous_edge;
        assert abs(measured - C_OUTPUT_PERIOD) <= C_TOLERANCE
          report "CLOCK_WIZARD_SELF_CHECK_STATUS: FAIL wrong output period" severity failure;
        assert locked = '1'
          report "CLOCK_WIZARD_SELF_CHECK_STATUS: FAIL lock dropped during measurement" severity failure;
        previous_edge := now;
      end loop;
      wait until falling_edge(clk_out1) for C_OUTPUT_PERIOD;
      assert falling_edge(clk_out1)
        report "CLOCK_WIZARD_SELF_CHECK_STATUS: FAIL missing falling edge" severity failure;
      measured := now - previous_edge;
      assert abs(measured - C_OUTPUT_HIGH) <= C_TOLERANCE
        report "CLOCK_WIZARD_SELF_CHECK_STATUS: FAIL wrong duty cycle" severity failure;
      record_event(event_name);
    end procedure;
  begin
    wait for 200 ns;
    p_reset <= ${reset_inactive};
    wait until locked = '1' for 100 us;
    assert locked = '1'
      report "CLOCK_WIZARD_SELF_CHECK_STATUS: FAIL initial lock timeout" severity failure;
    record_event("INITIAL_LOCK");
    measure_output("PERIOD_BEFORE_RESET");

    wait for 3 ns;
    p_reset <= ${reset_asserted};
    wait for 2 ns;
    assert locked = '0'
      report "CLOCK_WIZARD_SELF_CHECK_STATUS: FAIL reset did not clear lock" severity failure;
    record_event("RESET_UNLOCK");
    wait for 200 ns;
    p_reset <= ${reset_inactive};
    wait until locked = '1' for 100 us;
    assert locked = '1'
      report "CLOCK_WIZARD_SELF_CHECK_STATUS: FAIL relock timeout" severity failure;
    record_event("RELOCK");
    measure_output("PERIOD_AFTER_RESET");

    report "CLOCK_WIZARD_SELF_CHECK_STATUS: PASS" severity note;
    finish;
    wait;
  end process;

  watchdog : process
  begin
    wait for 250 us;
    assert false report "CLOCK_WIZARD_SELF_CHECK_STATUS: FAIL watchdog timeout" severity failure;
  end process;
end architecture;

library ieee;
use ieee.std_logic_1164.all;
use std.textio.all;
use std.env.all;

entity tb_fit_timer_selfcheck is
end entity;

architecture sim of tb_fit_timer_selfcheck is
  constant C_MINIMUM_PERIOD : positive := $minimum_period;
  constant C_MAXIMUM_PERIOD : positive := $maximum_period;
  constant C_FIRST_TIMEOUT : positive := $first_timeout;
  signal Clk : std_logic := '0';
  signal Rst : std_logic := $reset_asserted;
  signal Interrupt : std_logic;
begin
  Clk <= not Clk after 5 ns;

  dut : entity work.dut_0
    port map (Clk => Clk, Rst => Rst, Interrupt => Interrupt);

  stimulus : process
    file actual_file : text open write_mode is "$actual_path";
    variable output_line : line;

    procedure record_event(constant value : in string) is
    begin
      write(output_line, value);
      writeline(actual_file, output_line);
      flush(actual_file);
    end procedure;

    procedure assert_known_low(constant check_name : in string) is
    begin
      assert Interrupt = '0'
        report "FIT_TIMER_SELF_CHECK_STATUS: FAIL " & check_name severity failure;
    end procedure;

    procedure wait_for_first_interrupt is
    begin
      for cycle in 1 to C_FIRST_TIMEOUT loop
        wait until rising_edge(Clk);
        wait for 1 ps;
        assert Interrupt = '0' or Interrupt = '1'
          report "FIT_TIMER_SELF_CHECK_STATUS: FAIL unknown interrupt" severity failure;
        if Interrupt = '1' then
          return;
        end if;
      end loop;
      assert false report "FIT_TIMER_SELF_CHECK_STATUS: FAIL first interrupt timeout" severity failure;
    end procedure;

    procedure measure_periods(constant count : in positive) is
      variable elapsed : natural;
    begin
      for sample in 1 to count loop
        wait until rising_edge(Clk);
        wait for 1 ps;
        assert_known_low("interrupt wider than one clock");
        elapsed := 1;
        loop
          wait until rising_edge(Clk);
          wait for 1 ps;
          elapsed := elapsed + 1;
          assert Interrupt = '0' or Interrupt = '1'
            report "FIT_TIMER_SELF_CHECK_STATUS: FAIL unknown interrupt" severity failure;
          exit when Interrupt = '1';
          assert elapsed <= C_MAXIMUM_PERIOD
            report "FIT_TIMER_SELF_CHECK_STATUS: FAIL interrupt period too long" severity failure;
        end loop;
        assert elapsed >= C_MINIMUM_PERIOD and elapsed <= C_MAXIMUM_PERIOD
          report "FIT_TIMER_SELF_CHECK_STATUS: FAIL wrong interrupt period" severity failure;
      end loop;
    end procedure;
  begin
    for cycle in 1 to 20 loop
      wait until rising_edge(Clk);
      wait for 1 ps;
      assert_known_low("interrupt asserted during reset");
    end loop;
    record_event("RESET_SUPPRESSION");

    wait until falling_edge(Clk);
    Rst <= $reset_inactive;
    wait_for_first_interrupt;
    record_event("FIRST_INTERRUPT");
    measure_periods(4);
    record_event("PERIODS_BEFORE_RESET");

    wait until falling_edge(Clk);
    Rst <= $reset_asserted;
    for cycle in 1 to 20 loop
      wait until rising_edge(Clk);
      wait for 1 ps;
      assert_known_low("runtime reset did not suppress interrupt");
    end loop;
    record_event("RUNTIME_RESET");

    wait until falling_edge(Clk);
    Rst <= $reset_inactive;
    wait_for_first_interrupt;
    record_event("FIRST_INTERRUPT_AFTER_RESET");
    measure_periods(2);
    record_event("PERIODS_AFTER_RESET");

    report "FIT_TIMER_SELF_CHECK_STATUS: PASS" severity note;
    finish;
    wait;
  end process;

  watchdog : process
  begin
    wait for $watchdog_ns ns;
    assert false report "FIT_TIMER_SELF_CHECK_STATUS: FAIL watchdog timeout" severity failure;
  end process;
end architecture;

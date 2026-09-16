library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_textio.all;
use std.textio.all;
use std.env.all;

entity tb_cycle_selfcheck is
end entity;

architecture sim of tb_cycle_selfcheck is
  signal clk : std_logic := '0';
  signal p_B : std_logic_vector(7 downto 0) := (others => '0');
  signal p_ADD : std_logic := '0';
  signal p_CE : std_logic := '0';
  signal p_SCLR : std_logic := '0';
  signal p_BYPASS : std_logic := '0';
  signal p_Q : std_logic_vector(15 downto 0) := (others => '0');
begin
  dut : entity work.dut_0
    port map (
      B => p_B,
      ADD => p_ADD,
      CE => p_CE,
      SCLR => p_SCLR,
      BYPASS => p_BYPASS,
      Q => p_Q,
      CLK => clk
    );

  stimulus_and_checker : process
    file inputs : text open read_mode is "<REPOSITORY_ROOT>/runs/batches/2026-09-14_22-02-51_UTC+0800_04f9f225/accumulator/acc_signed_control/vectors/input_vectors.txt";
    file expected_file : text open read_mode is "<REPOSITORY_ROOT>/runs/batches/2026-09-14_22-02-51_UTC+0800_04f9f225/accumulator/acc_signed_control/vectors/expected_output.txt";
    file actual_file : text open write_mode is "<REPOSITORY_ROOT>/runs/batches/2026-09-14_22-02-51_UTC+0800_04f9f225/accumulator/acc_signed_control/outputs/actual_output.txt";
    variable input_line, expected_line, output_line : line;
    variable stimulus : std_logic_vector(12 - 1 downto 0);
    variable expected, actual : std_logic_vector(16 - 1 downto 0);
    variable count : natural := 0;
  begin
    wait for 200 ns;
    while not endfile(inputs) loop
      assert not endfile(expected_file)
        report "CYCLE_SELF_CHECK_STATUS: FAIL missing expected row" severity failure;
      readline(inputs, input_line);
      read(input_line, stimulus);
      readline(expected_file, expected_line);
      read(expected_line, expected);
      p_B <= stimulus(11 downto 4);
      p_ADD <= stimulus(3);
      p_CE <= stimulus(2);
      p_SCLR <= stimulus(1);
      p_BYPASS <= stimulus(0);
      wait for 5 ns;
      clk <= '1';
      wait for 1 ns;
      actual(15 downto 0) := p_Q;
      write(output_line, actual);
      writeline(actual_file, output_line);
      flush(actual_file);
      assert not is_x(actual) and actual = expected
        report "CYCLE_SELF_CHECK_STATUS: FAIL cycle=" & integer'image(count) &
               " expected=" & to_string(expected) & " actual=" & to_string(actual)
        severity failure;
      count := count + 1;
      wait for 4 ns;
      clk <= '0';
    end loop;
    assert count = 535 and count > 0 and endfile(expected_file)
      report "CYCLE_SELF_CHECK_STATUS: FAIL row count" severity failure;
    report "CYCLE_SELF_CHECK_STATUS: PASS";
    finish;
    wait;
  end process;

  watchdog : process
  begin
    wait for 5650 ns;
    assert false report "CYCLE_SELF_CHECK_STATUS: FAIL timeout" severity failure;
    wait;
  end process;
end architecture;

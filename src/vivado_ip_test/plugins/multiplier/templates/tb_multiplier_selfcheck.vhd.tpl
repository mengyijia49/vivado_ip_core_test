library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_textio.all;
use std.textio.all;

entity tb_multiplier_selfcheck is
end entity;

architecture test of tb_multiplier_selfcheck is
  constant CLOCK_PERIOD : time := 10 ns;
  constant SAMPLE_DELAY : time := 1 ps;
  constant A_WIDTH : positive := ${a_width};
  constant B_WIDTH : positive := ${b_width};
  constant OUTPUT_WIDTH : positive := ${output_width};
  constant LATENCY : positive := ${latency};
  constant VECTOR_COUNT : positive := ${vector_count};
  constant TIMEOUT_CYCLES : positive := ${timeout_cycles};
  constant INPUT_FILE_PATH : string := "${input_path}";
  constant EXPECTED_FILE_PATH : string := "${expected_path}";
  constant ACTUAL_FILE_PATH : string := "${actual_path}";

  signal clk : std_logic := '0';
  signal a : std_logic_vector(A_WIDTH - 1 downto 0) := (others => '0');
  signal b : std_logic_vector(B_WIDTH - 1 downto 0) := (others => '0');
  signal p : std_logic_vector(OUTPUT_WIDTH - 1 downto 0);
  signal stimulus_started : std_logic := '0';
begin
  clk <= not clk after CLOCK_PERIOD / 2;

  dut : entity work.mult_gen_0
    port map (
      CLK => clk,
      A => a,
      B => b,
      P => p
    );

  stimulus : process
    file input_file : text open read_mode is INPUT_FILE_PATH;
    variable input_line : line;
    variable a_bits : bit_vector(A_WIDTH - 1 downto 0);
    variable b_bits : bit_vector(B_WIDTH - 1 downto 0);
  begin
    for cycle in 1 to 2 loop
      wait until rising_edge(clk);
    end loop;
    wait until falling_edge(clk);

    while not endfile(input_file) loop
      readline(input_file, input_line);
      read(input_line, a_bits);
      read(input_line, b_bits);
      a <= to_stdlogicvector(a_bits);
      b <= to_stdlogicvector(b_bits);
      stimulus_started <= '1';
      wait until rising_edge(clk);
    end loop;

    a <= (others => '0');
    b <= (others => '0');
    wait;
  end process;

  monitor : process
    file expected_file : text open read_mode is EXPECTED_FILE_PATH;
    file actual_file : text open write_mode is ACTUAL_FILE_PATH;
    variable expected_line : line;
    variable actual_line : line;
    variable expected_bits : bit_vector(OUTPUT_WIDTH - 1 downto 0);
    variable output_index : natural := 0;
  begin
    wait until stimulus_started = '1';
    for cycle in 1 to LATENCY - 1 loop
      wait until rising_edge(clk);
    end loop;

    while output_index < VECTOR_COUNT loop
      wait until rising_edge(clk);
      wait for SAMPLE_DELAY;
      assert not endfile(expected_file)
        report "MULTIPLIER_SELF_CHECK_STATUS: FAIL unexpected output"
        severity failure;
      readline(expected_file, expected_line);
      read(expected_line, expected_bits);
      write(actual_line, p);
      writeline(actual_file, actual_line);
      flush(actual_file);
      assert p = to_stdlogicvector(expected_bits)
        report "MULTIPLIER_SELF_CHECK_STATUS: FAIL mismatch at output"
          & integer'image(output_index)
          & " expected=" & to_string(to_stdlogicvector(expected_bits))
          & " actual=" & to_string(p)
        severity failure;
      output_index := output_index + 1;
    end loop;

    assert endfile(expected_file)
      report "MULTIPLIER_SELF_CHECK_STATUS: FAIL missing output"
      severity failure;
    report "MULTIPLIER_SELF_CHECK_STATUS: PASS" severity failure;
    wait;
  end process;

  timeout_guard : process
  begin
    wait for TIMEOUT_CYCLES * CLOCK_PERIOD;
    report "MULTIPLIER_SELF_CHECK_STATUS: FAIL timeout" severity failure;
    wait;
  end process;
end architecture;

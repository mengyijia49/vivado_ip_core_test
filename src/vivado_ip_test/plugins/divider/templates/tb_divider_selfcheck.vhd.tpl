library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_textio.all;
use std.textio.all;

entity tb_divider_selfcheck is
end entity;

architecture test of tb_divider_selfcheck is
  constant CLOCK_PERIOD : time := 10 ns;
  constant SAMPLE_DELAY : time := 1 ps;
  constant DIVIDEND_WIDTH : positive := ${dividend_width};
  constant DIVISOR_WIDTH : positive := ${divisor_width};
  constant DOUT_WIDTH : positive := ${dout_width};
  constant LATENCY : positive := ${latency};
  constant VECTOR_COUNT : positive := ${vector_count};
  constant TIMEOUT_CYCLES : positive := ${timeout_cycles};
  constant INPUT_FILE_PATH : string := "${input_path}";
  constant EXPECTED_FILE_PATH : string := "${expected_path}";
  constant ACTUAL_FILE_PATH : string := "${actual_path}";
  constant GAPS_FILE_PATH : string := "${gaps_path}";

  signal aclk : std_logic := '0';
  signal s_axis_divisor_tvalid : std_logic := '0';
  signal s_axis_divisor_tdata : std_logic_vector(DIVISOR_WIDTH - 1 downto 0)
    := (others => '0');
  signal s_axis_dividend_tvalid : std_logic := '0';
  signal s_axis_dividend_tdata : std_logic_vector(DIVIDEND_WIDTH - 1 downto 0)
    := (others => '0');
  signal m_axis_dout_tvalid : std_logic;
  signal m_axis_dout_tdata : std_logic_vector(DOUT_WIDTH - 1 downto 0);
begin
  aclk <= not aclk after CLOCK_PERIOD / 2;

  dut : entity work.div_gen_0
    port map (
      aclk => aclk,
      s_axis_divisor_tvalid => s_axis_divisor_tvalid,
      s_axis_divisor_tdata => s_axis_divisor_tdata,
      s_axis_dividend_tvalid => s_axis_dividend_tvalid,
      s_axis_dividend_tdata => s_axis_dividend_tdata,
      m_axis_dout_tvalid => m_axis_dout_tvalid,
      m_axis_dout_tdata => m_axis_dout_tdata
    );

  stimulus : process
    file input_file : text open read_mode is INPUT_FILE_PATH;
    file gaps_file : text open read_mode is GAPS_FILE_PATH;
    variable gap_line : line;
    variable gap_cycles : natural;
    variable input_line : line;
    variable dividend_bits : bit_vector(DIVIDEND_WIDTH - 1 downto 0);
    variable divisor_bits : bit_vector(DIVISOR_WIDTH - 1 downto 0);
  begin
    for cycle in 1 to 3 loop
      wait until rising_edge(aclk);
    end loop;

    while not endfile(input_file) loop
      assert not endfile(gaps_file)
        report "DIVIDER_SELF_CHECK_STATUS: FAIL missing schedule" severity failure;
      readline(gaps_file, gap_line);
      read(gap_line, gap_cycles);
      s_axis_dividend_tvalid <= '0';
      s_axis_divisor_tvalid <= '0';
      for cycle in 1 to gap_cycles loop
        wait until rising_edge(aclk);
      end loop;
      readline(input_file, input_line);
      read(input_line, dividend_bits);
      read(input_line, divisor_bits);
      s_axis_dividend_tdata <= to_stdlogicvector(dividend_bits);
      s_axis_divisor_tdata <= to_stdlogicvector(divisor_bits);
      s_axis_dividend_tvalid <= '1';
      s_axis_divisor_tvalid <= '1';
      wait until rising_edge(aclk);
    end loop;

    assert endfile(gaps_file)
      report "DIVIDER_SELF_CHECK_STATUS: FAIL extra schedule" severity failure;

    s_axis_dividend_tvalid <= '0';
    s_axis_divisor_tvalid <= '0';
    s_axis_dividend_tdata <= (others => '0');
    s_axis_divisor_tdata <= (others => '0');
    wait;
  end process;

  monitor : process
    file expected_file : text open read_mode is EXPECTED_FILE_PATH;
    file actual_file : text open write_mode is ACTUAL_FILE_PATH;
    variable expected_line : line;
    variable actual_line : line;
    variable expected_bits : bit_vector(DOUT_WIDTH - 1 downto 0);
    variable output_index : natural := 0;
  begin
    while output_index < VECTOR_COUNT loop
      wait until rising_edge(aclk);
      wait for SAMPLE_DELAY;
      if m_axis_dout_tvalid = '1' then
        assert not endfile(expected_file)
          report "DIVIDER_SELF_CHECK_STATUS: FAIL unexpected output"
          severity failure;
        readline(expected_file, expected_line);
        read(expected_line, expected_bits);
        write(actual_line, m_axis_dout_tdata);
        writeline(actual_file, actual_line);
        flush(actual_file);
        assert m_axis_dout_tdata = to_stdlogicvector(expected_bits)
          report "DIVIDER_SELF_CHECK_STATUS: FAIL mismatch at output"
            & integer'image(output_index)
            & " expected=" & to_string(to_stdlogicvector(expected_bits))
            & " actual=" & to_string(m_axis_dout_tdata)
          severity failure;
        output_index := output_index + 1;
      end if;
    end loop;

    for cycle in 1 to LATENCY + 5 loop
      wait until rising_edge(aclk);
      wait for SAMPLE_DELAY;
      assert m_axis_dout_tvalid /= '1'
        report "DIVIDER_SELF_CHECK_STATUS: FAIL extra output"
        severity failure;
    end loop;

    assert endfile(expected_file)
      report "DIVIDER_SELF_CHECK_STATUS: FAIL missing output"
      severity failure;
    report "DIVIDER_SELF_CHECK_STATUS: PASS" severity failure;
    wait;
  end process;

  protocol_monitor : process
    variable valid_pipeline : std_logic_vector(LATENCY - 1 downto 0) := (others => '0');
    variable cycle_index : natural := 0;
  begin
    wait until rising_edge(aclk);
    for index in LATENCY - 1 downto 1 loop
      valid_pipeline(index) := valid_pipeline(index - 1);
    end loop;
    valid_pipeline(0) := s_axis_dividend_tvalid and s_axis_divisor_tvalid;
    wait for SAMPLE_DELAY;
    assert m_axis_dout_tvalid = valid_pipeline(LATENCY - 1)
      report "DIVIDER_SELF_CHECK_STATUS: FAIL valid timing at cycle"
        & integer'image(cycle_index)
        & " expected=" & std_logic'image(valid_pipeline(LATENCY - 1))
        & " actual=" & std_logic'image(m_axis_dout_tvalid)
      severity failure;
    cycle_index := cycle_index + 1;
  end process;

  timeout_guard : process
  begin
    wait for TIMEOUT_CYCLES * CLOCK_PERIOD;
    report "DIVIDER_SELF_CHECK_STATUS: FAIL timeout" severity failure;
    wait;
  end process;
end architecture;

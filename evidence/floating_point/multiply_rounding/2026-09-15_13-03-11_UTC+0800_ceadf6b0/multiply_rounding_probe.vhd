library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;

entity tb_floating_multiply_probe is
end entity;

architecture sim of tb_floating_multiply_probe is
  type words_t is array(0 to 15) of std_logic_vector(63 downto 0);
  constant input_a : words_t := (
    x"3FEFFFFFFFFFFFFE", x"3FEFFFFFFFFFFFFE", x"3FF0000000000000", x"4000000000000000",
    x"3FEFFFFFFFFFFFFE", x"3FEFFFFFFFFFFFFF", x"3FEFFFFFFFFFFFFD", x"3FEFFFFFFFFFFFFE",
    x"BFEFFFFFFFFFFFFE", x"3FEFFFFFFFFFFFFE", x"BFEFFFFFFFFFFFFE", x"0000000000000000",
    x"7FEFFFFFFFFFFFFF", x"0010000000000000", x"7FF8000000000001", x"3FF0000000000001");
  constant input_b : words_t := (
    x"3C80000000000001", x"3FF0000000000001", x"3FF0000000000000", x"3FE0000000000000",
    x"3FF0000000000000", x"3FF0000000000001", x"3FF0000000000001", x"3FEFFFFFFFFFFFFF",
    x"3FF0000000000001", x"BFF0000000000001", x"BFF0000000000001", x"7FF0000000000000",
    x"4000000000000000", x"3FE0000000000000", x"3FF0000000000000", x"3FF0000000000001");
  constant expected : words_t := (
    x"3C80000000000000", x"3FF0000000000000", x"3FF0000000000000", x"3FF0000000000000",
    x"3FEFFFFFFFFFFFFE", x"3FF0000000000000", x"3FEFFFFFFFFFFFFF", x"3FEFFFFFFFFFFFFD",
    x"BFF0000000000000", x"BFF0000000000000", x"3FF0000000000000", x"7FF8000000000000",
    x"7FF0000000000000", x"0000000000000000", x"7FF8000000000000", x"3FF0000000000002");
  type flags_t is array(0 to 15) of std_logic_vector(2 downto 0);
  constant expected_flags : flags_t := (11 => "100", 12 => "010", 13 => "001", others => "000");
  signal clk : std_logic := '0';
  signal resetn, a_valid, b_valid, a_ready, b_ready, result_valid : std_logic := '0';
  signal a_data, b_data, result_data : std_logic_vector(63 downto 0) := (others => '0');
  signal result_flags : std_logic_vector(2 downto 0);
  signal accepted_a, accepted_b : natural := 0;
begin
  clk <= not clk after 5 ns;
  resetn <= '1' after 200 ns;
  dut : entity work.dut_0
    port map(aclk => clk, aresetn => resetn,
      s_axis_a_tdata => a_data, s_axis_a_tvalid => a_valid, s_axis_a_tready => a_ready,
      s_axis_b_tdata => b_data, s_axis_b_tvalid => b_valid, s_axis_b_tready => b_ready,
      m_axis_result_tdata => result_data, m_axis_result_tvalid => result_valid,
      m_axis_result_tready => '1', m_axis_result_tuser => result_flags);
  process
    variable a_done, b_done : boolean;
  begin
    wait until resetn = '1';
    for i in input_a'range loop
      wait until falling_edge(clk);
      a_data <= input_a(i);
      b_data <= input_b(i);
      a_valid <= '1'; b_valid <= '1';
      a_done := false; b_done := false;
      loop
        wait until rising_edge(clk);
        assert (a_ready = '0' or a_ready = '1') and (b_ready = '0' or b_ready = '1')
          report "FLOATING_MULTIPLY_PROBE_STATUS: FAIL unknown input ready" severity failure;
        if not a_done and a_ready = '1' then
          accepted_a <= accepted_a + 1;
          a_done := true;
        end if;
        if not b_done and b_ready = '1' then
          accepted_b <= accepted_b + 1;
          b_done := true;
        end if;
        wait until falling_edge(clk);
        if a_done then a_valid <= '0'; end if;
        if b_done then b_valid <= '0'; end if;
        exit when a_done and b_done;
      end loop;
    end loop;
    wait;
  end process;
  process
    variable count, failures, tail : natural := 0;
  begin
    wait until resetn = '1';
    loop
      wait until rising_edge(clk);
      assert result_valid = '0' or result_valid = '1'
        report "FLOATING_MULTIPLY_PROBE_STATUS: FAIL unknown output valid" severity failure;
      if result_valid = '1' then
        assert count < expected'length
          report "FLOATING_MULTIPLY_PROBE_STATUS: FAIL extra output" severity failure;
        report "FLOATING_MULTIPLY_SAMPLE " & integer'image(count) &
          " expected=" & to_hstring(expected(count)) & " actual=" & to_hstring(result_data) &
          " expected_flags=" & to_hstring(expected_flags(count)) & " flags=" & to_hstring(result_flags)
          severity note;
        if result_data /= expected(count) or result_flags /= expected_flags(count) then
          failures := failures + 1;
        end if;
        wait for 0 ns;
        assert count < accepted_a and count < accepted_b
          report "FLOATING_MULTIPLY_PROBE_STATUS: FAIL result before accepted operands" severity failure;
        count := count + 1;
      end if;
      if count = expected'length then
        tail := tail + 1;
        exit when tail = 128;
      end if;
    end loop;
    assert failures = 0 report "FLOATING_MULTIPLY_PROBE_STATUS: FAIL mismatches=" & integer'image(failures)
      severity failure;
    report "FLOATING_MULTIPLY_PROBE_STATUS: PASS" severity note;
    finish;
    wait;
  end process;
  process
  begin
    wait for 100 us;
    assert false report "FLOATING_MULTIPLY_PROBE_STATUS: FAIL timeout" severity failure;
    wait;
  end process;
end architecture;

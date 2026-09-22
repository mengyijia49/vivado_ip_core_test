library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;

entity tb_floating_reciprocal_single_probe is
end entity;

architecture sim of tb_floating_reciprocal_single_probe is
  type words_t is array(0 to 10) of std_logic_vector(31 downto 0);
  constant inputs : words_t := (
    x"00FFFFFE", x"00FFFFFF", x"01000000", x"80FFFFFE", x"80FFFFFF",
    x"3F800000", x"40400000", x"7F7FFFFF", x"00000000", x"7F800000", x"7FC00001");
  constant expected : words_t := (
    x"7E000001", x"7E000001", x"7E000000", x"FE000001", x"FE000001",
    x"3F800000", x"3EAAAAAB", x"00000000", x"7F800000", x"00000000", x"7FC00000");
  type flags_t is array(0 to 10) of std_logic_vector(1 downto 0);
  constant expected_flags : flags_t := (7 => "01", 8 => "10", others => "00");
  signal clk : std_logic := '0';
  signal resetn, input_valid, input_ready, result_valid : std_logic := '0';
  signal input_data, result_data : std_logic_vector(31 downto 0) := (others => '0');
  signal result_flags : std_logic_vector(1 downto 0);
  signal accepted : natural := 0;
begin
  clk <= not clk after 5 ns;
  resetn <= '1' after 200 ns;
  dut : entity work.dut_0
    port map(aclk => clk, aresetn => resetn,
      s_axis_a_tdata => input_data, s_axis_a_tvalid => input_valid,
      s_axis_a_tready => input_ready,
      m_axis_result_tdata => result_data, m_axis_result_tvalid => result_valid,
      m_axis_result_tready => '1', m_axis_result_tuser => result_flags);
  process
  begin
    wait until resetn = '1';
    for i in inputs'range loop
      wait until falling_edge(clk);
      input_data <= inputs(i);
      input_valid <= '1';
      loop
        wait until rising_edge(clk);
        assert input_ready = '0' or input_ready = '1'
          report "FLOATING_RECIPROCAL_STATUS: FAIL unknown input ready" severity failure;
        exit when input_ready = '1';
      end loop;
      accepted <= accepted + 1;
      wait until falling_edge(clk);
      input_valid <= '0';
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
        report "FLOATING_RECIPROCAL_STATUS: FAIL unknown output valid" severity failure;
      if result_valid = '1' then
        assert count < expected'length
          report "FLOATING_RECIPROCAL_STATUS: FAIL extra output" severity failure;
        report "FLOATING_RECIPROCAL_SAMPLE " & integer'image(count) &
          " expected=" & to_hstring(expected(count)) & " actual=" & to_hstring(result_data) &
          " expected_flags=" & to_hstring(expected_flags(count)) & " flags=" & to_hstring(result_flags)
          severity note;
        if result_data /= expected(count) or result_flags /= expected_flags(count) then
          failures := failures + 1;
        end if;
        wait for 0 ns;
        assert count < accepted
          report "FLOATING_RECIPROCAL_STATUS: FAIL result before accepted input" severity failure;
        count := count + 1;
      end if;
      if count = expected'length then
        tail := tail + 1;
        exit when tail = 128;
      end if;
    end loop;
    assert failures = 0 report "FLOATING_RECIPROCAL_STATUS: FAIL mismatches=" & integer'image(failures)
      severity failure;
    report "FLOATING_RECIPROCAL_STATUS: PASS" severity note;
    finish;
    wait;
  end process;
  process
  begin
    wait for 100 us;
    assert false report "FLOATING_RECIPROCAL_STATUS: FAIL timeout" severity failure;
    wait;
  end process;
end architecture;

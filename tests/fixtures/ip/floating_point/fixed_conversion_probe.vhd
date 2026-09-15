library ieee;
use ieee.std_logic_1164.all;
use std.env.all;

entity tb_floating_probe is
end entity;

architecture sim of tb_floating_probe is
  type words_t is array(natural range <>) of std_logic_vector(15 downto 0);
  type results_t is array(natural range <>) of std_logic_vector(9 downto 0);
  constant inputs : words_t := (x"0000", x"8000", x"3C00", x"4100", x"4300", x"C100",
    x"4780", x"C840", x"C880", x"7C00", x"FC00", x"7C01", x"7E00", x"FC01", x"03FF", x"0400", x"0001");
  -- Full output byte followed by INVALID_OP and OVERFLOW.
  constant expected : results_t := (x"00" & "00", x"00" & "00", x"01" & "00", x"02" & "00",
    x"04" & "00", x"FE" & "00", x"07" & "01", x"F8" & "00", x"F8" & "01",
    x"07" & "11", x"F8" & "11", x"F8" & "10", x"F8" & "10", x"F8" & "10",
    x"00" & "00", x"00" & "00", x"00" & "00");
  signal clk : std_logic := '0';
  signal resetn, source_valid, source_ready, sink_valid : std_logic := '0';
  signal source_data : std_logic_vector(15 downto 0) := (others => '0');
  signal sink_data : std_logic_vector(7 downto 0);
  signal sink_flags : std_logic_vector(1 downto 0);
begin
  clk <= not clk after 5 ns;
  resetn <= '1' after 200 ns;
  dut : entity work.dut_0
    port map (aclk => clk, aresetn => resetn,
      s_axis_a_tdata => source_data, s_axis_a_tvalid => source_valid,
      s_axis_a_tready => source_ready, m_axis_result_tdata => sink_data,
      m_axis_result_tvalid => sink_valid, m_axis_result_tready => '1', m_axis_result_tuser => sink_flags);
  process
  begin
    wait until resetn = '1';
    for i in inputs'range loop
      wait until falling_edge(clk);
      source_data <= inputs(i);
      source_valid <= '1';
      loop
        wait until rising_edge(clk);
        exit when source_ready = '1';
      end loop;
      wait until falling_edge(clk);
      source_valid <= '0';
    end loop;
    wait;
  end process;
  process
    variable count : natural := 0;
  begin
    wait until resetn = '1';
    loop
      wait until rising_edge(clk);
      assert sink_valid = '0' or sink_valid = '1'
        report "FLOATING_PROBE_STATUS: FAIL unknown valid" severity failure;
      if sink_valid = '1' then
        assert count < inputs'length
          report "FLOATING_PROBE_STATUS: FAIL extra output" severity failure;
        assert (sink_data & sink_flags) = expected(count)
          report "FLOATING_PROBE_STATUS: FAIL sample " & integer'image(count) severity failure;
        report "FLOATING_SAMPLE " & integer'image(count) & " PASS" severity note;
        count := count + 1;
        exit when count = inputs'length;
      end if;
    end loop;
    for i in 1 to 64 loop
      wait until rising_edge(clk);
      assert sink_valid = '0' report "FLOATING_PROBE_STATUS: FAIL extra output" severity failure;
    end loop;
    report "FLOATING_PROBE_STATUS: PASS" severity note;
    finish;
    wait;
  end process;
  process
  begin
    wait for 100 us;
    assert false report "FLOATING_PROBE_STATUS: FAIL timeout" severity failure;
    wait;
  end process;
end architecture;

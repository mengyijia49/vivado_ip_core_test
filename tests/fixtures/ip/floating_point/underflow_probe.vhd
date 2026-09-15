library ieee;
use ieee.std_logic_1164.all;
use std.env.all;

entity tb_floating_probe is
end entity;

architecture sim of tb_floating_probe is
  type words_t is array(natural range <>) of std_logic_vector(31 downto 0);
  type results_t is array(natural range <>) of std_logic_vector(17 downto 0);
  constant inputs : words_t := (x"387FDFFF", x"387FE000", x"387FEFFF", x"387FF000",
    x"387FF001", x"387FFFFF", x"38800000", x"B87FEFFF", x"B87FF000", x"B8800000",
    x"00000001", x"80000001", x"00000000", x"7F800000");
  -- PG060 main paragraph: round at full precision, then detect underflow.
  constant expected : results_t := (x"0000" & "01", x"0000" & "01", x"0000" & "01", x"0400" & "00",
    x"0400" & "00", x"0400" & "00", x"0400" & "00", x"8000" & "01", x"8400" & "00", x"8400" & "00",
    x"0000" & "00", x"8000" & "00", x"0000" & "00", x"7C00" & "00");
  signal clk : std_logic := '0';
  signal resetn, source_valid, source_ready, sink_valid : std_logic := '0';
  signal source_data : std_logic_vector(31 downto 0) := (others => '0');
  signal sink_data : std_logic_vector(15 downto 0);
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

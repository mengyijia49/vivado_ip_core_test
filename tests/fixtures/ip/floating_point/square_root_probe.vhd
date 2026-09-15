library ieee;
use ieee.std_logic_1164.all;
use std.env.all;

entity tb_floating_probe is
end entity;

architecture sim of tb_floating_probe is
  type words_t is array(natural range <>) of std_logic_vector(15 downto 0);
  constant inputs : words_t := (x"0000", x"8000", x"0001", x"83FF", x"0400", x"7BFF",
    x"3C00", x"4000", x"4200", x"4400", x"4880", x"4C00", x"3400", x"3BFF", x"3C01",
    x"3C02", x"BC00", x"FC00", x"7C00", x"7C01", x"FC01", x"7E00");
  constant expected : words_t := (x"0000", x"8000", x"0000", x"8000", x"2000", x"5BFF",
    x"3C00", x"3DA8", x"3EEE", x"4000", x"4200", x"4400", x"3800", x"3BFF", x"3C00",
    x"3C01", x"7E00", x"7E00", x"7C00", x"7E00", x"7E00", x"7E00");
  signal clk : std_logic := '0';
  signal resetn, source_valid, source_ready, sink_valid, sink_ready : std_logic := '0';
  signal source_data : std_logic_vector(15 downto 0) := (others => '0');
  signal sink_data : std_logic_vector(15 downto 0);
  signal sink_flags : std_logic_vector(0 downto 0);
begin
  clk <= not clk after 5 ns;
  resetn <= '1' after 200 ns;
  dut : entity work.dut_0
    port map (aclk => clk, aresetn => resetn,
      s_axis_a_tdata => source_data, s_axis_a_tvalid => source_valid,
      s_axis_a_tready => source_ready, m_axis_result_tdata => sink_data,
      m_axis_result_tvalid => sink_valid, m_axis_result_tready => sink_ready, m_axis_result_tuser => sink_flags);
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
    variable cycle : natural := 0;
  begin
    wait until resetn = '1';
    loop
      wait until falling_edge(clk);
      cycle := cycle + 1;
      if cycle mod 31 < 9 then
        sink_ready <= '0';
      else
        sink_ready <= '1';
      end if;
    end loop;
  end process;
  process
    variable count, tail : natural := 0;
    variable invalid : std_logic;
    variable stalled : boolean := false;
    variable held : std_logic_vector(16 downto 0);
  begin
    wait until resetn = '1';
    loop
      wait until rising_edge(clk);
      assert sink_valid = '0' or sink_valid = '1'
        report "FLOATING_PROBE_STATUS: FAIL unknown valid" severity failure;
      if stalled then
        assert sink_valid = '1' and (sink_data & sink_flags) = held
          report "FLOATING_PROBE_STATUS: FAIL changed under backpressure" severity failure;
      end if;
      stalled := sink_valid = '1' and sink_ready = '0';
      held := sink_data & sink_flags;
      if sink_valid = '1' and sink_ready = '1' then
        assert count < inputs'length
          report "FLOATING_PROBE_STATUS: FAIL extra output" severity failure;
        invalid := '0';
        if count = 16 or count = 17 then
          invalid := '1';
        end if;
        assert sink_data = expected(count) and sink_flags(0) = invalid
          report "FLOATING_PROBE_STATUS: FAIL sample " & integer'image(count) severity failure;
        report "FLOATING_SAMPLE " & integer'image(count) & " PASS" severity note;
        count := count + 1;
      end if;
      if count = inputs'length then
        tail := tail + 1;
        exit when tail = 128;
      end if;
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

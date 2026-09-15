library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;

entity tb_cordic_probe is
end entity;

architecture sim of tb_cordic_probe is
  type values_t is array(natural range <>) of natural;
  constant inputs : values_t := (0, 1, 2, 3, 4, 6, 7, 8, 9, 255);
  signal clk : std_logic := '0';
  signal resetn, source_valid, source_ready, sink_valid : std_logic := '0';
  signal source_data, sink_data : std_logic_vector(7 downto 0) := (others => '0');
begin
  clk <= not clk after 5 ns;
  resetn <= '1' after 200 ns;
  dut : entity work.dut_0
    port map (aclk => clk, aresetn => resetn,
      s_axis_cartesian_tdata => source_data, s_axis_cartesian_tvalid => source_valid,
      s_axis_cartesian_tready => source_ready, m_axis_dout_tdata => sink_data,
      m_axis_dout_tvalid => sink_valid, m_axis_dout_tready => '1');
  process
  begin
    wait until resetn = '1';
    for i in inputs'range loop
      wait until falling_edge(clk);
      source_data <= std_logic_vector(to_unsigned(inputs(i), 8));
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
        report "CORDIC_PROBE_STATUS: FAIL unknown valid" severity failure;
      if sink_valid = '1' then
        assert count < inputs'length and not is_x(sink_data)
          report "CORDIC_PROBE_STATUS: FAIL unexpected output" severity failure;
        report "CORDIC_SAMPLE input=" & integer'image(inputs(count)) &
               " output=" & integer'image(to_integer(unsigned(sink_data))) severity note;
        count := count + 1;
        exit when count = inputs'length;
      end if;
    end loop;
    for i in 1 to 64 loop
      wait until rising_edge(clk);
      assert sink_valid = '0' report "CORDIC_PROBE_STATUS: FAIL extra output" severity failure;
    end loop;
    report "CORDIC_PROBE_STATUS: PASS" severity note;
    finish;
    wait;
  end process;
  process
  begin
    wait for 100 us;
    assert false report "CORDIC_PROBE_STATUS: FAIL timeout" severity failure;
    wait;
  end process;
end architecture;

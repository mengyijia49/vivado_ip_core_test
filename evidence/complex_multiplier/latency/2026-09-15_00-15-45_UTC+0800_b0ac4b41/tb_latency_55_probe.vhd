library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;

entity tb_latency_55_probe is
end entity;

architecture sim of tb_latency_55_probe is
  signal clk : std_logic := '0';
  signal a, b : std_logic_vector(15 downto 0) := (others => '0');
  signal valid_in, valid_out : std_logic := '0';
  signal result : std_logic_vector(31 downto 0);
begin
  clk <= not clk after 5 ns;
  dut : entity work.dut_0
    port map (aclk => clk, s_axis_a_tdata => a, s_axis_b_tdata => b,
              s_axis_a_tvalid => valid_in, s_axis_b_tvalid => valid_in,
              m_axis_dout_tvalid => valid_out, m_axis_dout_tdata => result);

  process
    variable expected : std_logic_vector(31 downto 0);
  begin
    for cycle in 0 to 160 loop
      wait until falling_edge(clk);
      valid_in <= '1';
      a <= x"0000";
      b <= x"0001";
      if cycle = 80 then
        a <= x"0002";
      end if;
      wait until rising_edge(clk);
      wait for 1 ns;
      expected := (others => '0');
      -- 2 * 1, truncated from 17 to 16 bits, is 1 at input cycle + 55 - 1.
      if cycle = 134 then
        expected := x"00000001";
      end if;
      if cycle >= 54 then
        assert valid_out = '1' and result = expected
          report "CMPY_LATENCY_PROBE: FAIL cycle=" & integer'image(cycle) &
                 " expected=" & to_hstring(expected) & " actual=" & to_hstring(result)
          severity failure;
      end if;
    end loop;
    report "CMPY_LATENCY_PROBE: PASS";
    stop;
    wait;
  end process;
end architecture;

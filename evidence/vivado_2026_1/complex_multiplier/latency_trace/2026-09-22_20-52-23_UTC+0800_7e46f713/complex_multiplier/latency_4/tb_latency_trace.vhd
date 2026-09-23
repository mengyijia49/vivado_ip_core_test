library ieee;
use ieee.std_logic_1164.all;
use std.env.all;

entity tb_latency_trace is
end entity;

architecture sim of tb_latency_trace is
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
    variable before_edge : std_logic_vector(31 downto 0);
  begin
    for cycle in 0 to 239 loop
      wait until falling_edge(clk);
      valid_in <= '1';
      a <= x"0000";
      b <= x"0001";
      if cycle = 80 then
        a <= x"0002";
      elsif cycle = 160 then
        a <= x"0006";
      end if;
      if cycle >= 150 and cycle <= 152 then
        valid_in <= '0';
        a <= x"0004";
      end if;
      wait for 1 ns;
      before_edge := result;
      wait until rising_edge(clk);
      wait for 1 ns;
      report "CMPY_TRACE cycle=" & integer'image(cycle) &
             " input=" & to_hstring(a) & " vin=" & std_logic'image(valid_in) &
             " before=" & to_hstring(before_edge) &
             " output=" & to_hstring(result) & " vout=" & std_logic'image(valid_out);
    end loop;
    report "CMPY_TRACE: COMPLETE";
    stop;
    wait;
  end process;
end architecture;

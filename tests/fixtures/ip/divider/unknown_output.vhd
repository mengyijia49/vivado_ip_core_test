library ieee;
use ieee.std_logic_1164.all;

entity div_gen_0 is
  port (
    aclk, s_axis_divisor_tvalid, s_axis_dividend_tvalid : in std_logic;
    s_axis_divisor_tdata, s_axis_dividend_tdata : in std_logic_vector(1 downto 0);
    m_axis_dout_tvalid : out std_logic;
    m_axis_dout_tdata : out std_logic_vector(3 downto 0)
  );
end entity;

architecture injected of div_gen_0 is
begin
  process(aclk)
  begin
    if rising_edge(aclk) then
      m_axis_dout_tvalid <= s_axis_divisor_tvalid and s_axis_dividend_tvalid;
      m_axis_dout_tdata <= (others => 'X');
    end if;
  end process;
end architecture;

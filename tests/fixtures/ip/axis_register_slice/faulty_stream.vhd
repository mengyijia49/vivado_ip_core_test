library ieee;
use ieee.std_logic_1164.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (
    aclk, aresetn : in std_logic;
    s_axis_tvalid : in std_logic;
    s_axis_tready : out std_logic;
    s_axis_tdata : in std_logic_vector(7 downto 0);
    m_axis_tvalid : out std_logic;
    m_axis_tready : in std_logic;
    m_axis_tdata : out std_logic_vector(7 downto 0)
  );
end entity;

architecture injected of dut_0 is
  signal corrupt : std_logic := '0';
begin
  s_axis_tready <= '1' when fault_mode = 4 else m_axis_tready;
  m_axis_tvalid <= '0' when aresetn = '0' or fault_mode = 4 else
                  '1' when fault_mode = 3 else s_axis_tvalid;
  m_axis_tdata <= (others => 'X') when fault_mode = 1 else
                 s_axis_tdata xor (corrupt & "0000000") when fault_mode = 2 else
                 s_axis_tdata xor "10000000" when fault_mode = 5 else s_axis_tdata;
  process(aclk)
  begin
    if rising_edge(aclk) then
      if aresetn = '0' then
        corrupt <= '0';
      elsif s_axis_tvalid = '1' and m_axis_tready = '0' then
        corrupt <= not corrupt;
      end if;
    end if;
  end process;
end architecture;

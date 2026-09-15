library ieee;
use ieee.std_logic_1164.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (
    aclk, aresetn : in std_logic;
    s_axis_tvalid : in std_logic;
    s_axis_tready : out std_logic;
    s_axis_tdata, s_axis_tuser : in std_logic_vector(7 downto 0);
    m_axis_tvalid : out std_logic;
    m_axis_tready : in std_logic;
    m_axis_tdata : out std_logic_vector(23 downto 0);
    m_axis_tuser : out std_logic_vector(7 downto 0);
    m_axis_tlast : out std_logic
  );
end entity;

architecture injected of dut_0 is
  signal phase : natural range 0 to 2 := 0;
  signal accepted : natural := 0;
begin
  s_axis_tready <= m_axis_tready;
  m_axis_tvalid <= s_axis_tvalid when aresetn = '1' else '0';
  m_axis_tdata <= x"A5" & s_axis_tdata & s_axis_tuser when fault_mode = 3 else
                 x"A5" & s_axis_tuser & s_axis_tdata;
  m_axis_tuser <= s_axis_tuser when fault_mode = 4 else s_axis_tdata;
  m_axis_tlast <= '1' when fault_mode = 2 and phase = 1 else
                 '0' when fault_mode = 2 or (fault_mode = 5 and accepted >= 3) else
                 '1' when phase = 2 else '0';
  process(aclk)
  begin
    if rising_edge(aclk) then
      if aresetn = '0' then
        phase <= 0;
        accepted <= 0;
      else
        if fault_mode = 1 or (s_axis_tvalid = '1' and s_axis_tready = '1') then
          phase <= (phase + 1) mod 3;
        end if;
        if s_axis_tvalid = '1' and s_axis_tready = '1' then
          accepted <= accepted + 1;
        end if;
      end if;
    end if;
  end process;
end architecture;

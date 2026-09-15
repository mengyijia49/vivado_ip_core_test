library ieee;
use ieee.std_logic_1164.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (
    aclk, aresetn : in std_logic;
    s_axis_tvalid : in std_logic;
    s_axis_tready : out std_logic;
    s_axis_tdata : in std_logic_vector(7 downto 0);
    s_axis_tkeep, s_axis_tstrb : in std_logic_vector(0 downto 0);
    s_axis_tlast : in std_logic;
    s_axis_tid, s_axis_tdest : in std_logic_vector(0 downto 0);
    s_axis_tuser : in std_logic_vector(1 downto 0);
    m_axis_tvalid : out std_logic;
    m_axis_tready : in std_logic;
    m_axis_tdata : out std_logic_vector(15 downto 0);
    m_axis_tkeep, m_axis_tstrb : out std_logic_vector(1 downto 0);
    m_axis_tlast : out std_logic;
    m_axis_tid, m_axis_tdest : out std_logic_vector(0 downto 0);
    m_axis_tuser : out std_logic_vector(3 downto 0)
  );
end entity;

architecture injected of dut_0 is
  signal toggle : std_logic := '0';
  signal accepted : natural := 0;
begin
  s_axis_tready <= '0' when fault_mode = 7 else m_axis_tready;
  m_axis_tvalid <= '0' when aresetn = '0' else
                  '1' when fault_mode = 6 and accepted = 4 else s_axis_tvalid;
  -- Null bytes may change; a position byte has no defined data value.
  m_axis_tdata(15 downto 8) <= (others => toggle);
  m_axis_tdata(7 downto 0) <= (others => 'X') when s_axis_tstrb(0) = '0' else
      s_axis_tdata xor "00000001" when fault_mode = 1 else
      s_axis_tdata xor (toggle & "0000000") when fault_mode = 5 else
      'X' & s_axis_tdata(6 downto 0) when fault_mode = 8 else s_axis_tdata;
  m_axis_tkeep <= "00" when fault_mode = 9 and s_axis_tstrb(0) = '0' else
                  '0' & s_axis_tkeep;
  m_axis_tstrb <= '1' & s_axis_tstrb when fault_mode = 4 else '0' & s_axis_tstrb;
  m_axis_tlast <= '0' when fault_mode = 2 else s_axis_tlast;
  m_axis_tid <= s_axis_tid;
  m_axis_tdest <= s_axis_tdest;
  m_axis_tuser <= "XX" & (s_axis_tuser xor "01") when fault_mode = 3 else "XX" & s_axis_tuser;
  process(aclk)
  begin
    if rising_edge(aclk) then
      if aresetn = '0' then
        toggle <= '0';
        accepted <= 0;
      else
        toggle <= not toggle;
        if s_axis_tvalid = '1' and s_axis_tready = '1' then
          accepted <= accepted + 1;
        end if;
      end if;
    end if;
  end process;
end architecture;

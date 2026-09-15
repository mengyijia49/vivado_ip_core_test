library ieee;
use ieee.std_logic_1164.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (
    aclk, aresetn : in std_logic;
    s_axis_tvalid : in std_logic_vector(1 downto 0);
    s_axis_tready : out std_logic_vector(1 downto 0);
    s_axis_tdata : in std_logic_vector(15 downto 0);
    s_axis_tuser : in std_logic_vector(7 downto 0);
    s_axis_tid : in std_logic_vector(3 downto 0);
    s_axis_tdest : in std_logic_vector(5 downto 0);
    s_axis_tlast : in std_logic_vector(1 downto 0);
    m_axis_tvalid : out std_logic;
    m_axis_tready : in std_logic;
    m_axis_tdata : out std_logic_vector(15 downto 0);
    m_axis_tuser : out std_logic_vector(7 downto 0);
    m_axis_tid : out std_logic_vector(1 downto 0);
    m_axis_tdest : out std_logic_vector(2 downto 0);
    m_axis_tlast : out std_logic
  );
end entity;

architecture fixture of dut_0 is
  signal changing : std_logic := '0';
begin
  process(all)
    variable valid : std_logic;
    variable ready : std_logic_vector(1 downto 0);
    variable data : std_logic_vector(15 downto 0);
  begin
    valid := and s_axis_tvalid;
    ready := (s_axis_tvalid(0) and m_axis_tready) & (s_axis_tvalid(1) and m_axis_tready);
    data := s_axis_tdata;
    m_axis_tuser <= s_axis_tuser;
    m_axis_tlast <= s_axis_tlast(1);
    m_axis_tid <= s_axis_tid(3 downto 2);
    m_axis_tdest <= s_axis_tdest(5 downto 3);
    case fault_mode is
      when 1 => valid := or s_axis_tvalid;
      when 2 => data := s_axis_tdata(7 downto 0) & s_axis_tdata(15 downto 8);
      when 3 => m_axis_tlast <= s_axis_tlast(0);
      when 4 => m_axis_tid <= s_axis_tid(1 downto 0);
      when 5 => m_axis_tdest <= s_axis_tdest(2 downto 0);
      when 6 => m_axis_tuser <= s_axis_tuser(3 downto 0) & s_axis_tuser(7 downto 4);
      when 7 => data(0) := data(0) xor changing;
      when 8 => valid := 'X';
      when 9 => valid := '0'; ready := "00";
      when 10 => ready(0) := '0';
      when 11 => ready(0) := 'X';
      when others => null;
    end case;
    if aresetn = '0' then
      valid := '0';
      ready := "00";
    end if;
    m_axis_tvalid <= valid;
    s_axis_tready <= ready;
    m_axis_tdata <= data;
  end process;
  process(aclk)
  begin
    if rising_edge(aclk) then
      changing <= not changing;
    end if;
  end process;
end architecture;

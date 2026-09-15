library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (
    aclk, aresetn, s_axis_tvalid : in std_logic;
    s_axis_tready : out std_logic;
    s_axis_tdata : in std_logic_vector(15 downto 0);
    s_axis_tuser : in std_logic_vector(7 downto 0);
    s_axis_tlast : in std_logic;
    m_axis_tvalid : out std_logic_vector(1 downto 0);
    m_axis_tready : in std_logic_vector(1 downto 0);
    m_axis_tdata : out std_logic_vector(31 downto 0);
    m_axis_tuser : out std_logic_vector(15 downto 0);
    m_axis_tlast : out std_logic_vector(1 downto 0)
  );
end entity;

architecture fixture of dut_0 is
  signal consumed : std_logic_vector(1 downto 0) := "00";
  signal valid : std_logic_vector(1 downto 0);
  signal ready : std_logic;
  signal changing : std_logic := '0';
begin
  process(all)
    variable v : std_logic_vector(1 downto 0);
    variable d : std_logic_vector(15 downto 0);
  begin
    v := (not consumed) and (1 downto 0 => s_axis_tvalid);
    ready <= and (consumed or m_axis_tready);
    d := s_axis_tdata(7 downto 0) & s_axis_tdata(15 downto 8);
    m_axis_tuser <= s_axis_tuser(0) & s_axis_tuser(7 downto 1) & s_axis_tuser;
    m_axis_tlast <= (others => s_axis_tlast);
    case fault_mode is
      when 1 => v := (others => s_axis_tvalid);
      when 2 => v(1) := '0'; ready <= '0';
      when 3 => d(0) := not d(0);
      when 4 => d(0) := d(0) xor changing;
      when 5 => m_axis_tuser <= s_axis_tuser & s_axis_tuser;
      when 6 => v(1) := 'X';
      when 7 => v(1) := '1';
      when 8 => ready <= '1';
      when others => null;
    end case;
    if aresetn = '0' then
      v := "00";
      ready <= '0';
    end if;
    valid <= v;
    m_axis_tdata <= d & s_axis_tdata;
  end process;
  m_axis_tvalid <= valid;
  s_axis_tready <= ready;
  process(aclk)
  begin
    if rising_edge(aclk) then
      changing <= not changing;
      if aresetn = '0' then
        consumed <= "00";
      elsif s_axis_tvalid = '1' and ready = '1' then
        consumed <= "00";
      else
        consumed <= consumed or (valid and m_axis_tready);
      end if;
    end if;
  end process;
end architecture;

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (
    aclk, aresetn : in std_logic;
    s_axis_cartesian_tdata : in std_logic_vector(7 downto 0);
    s_axis_cartesian_tvalid, s_axis_cartesian_tlast : in std_logic;
    s_axis_cartesian_tuser : in std_logic_vector(2 downto 0);
    s_axis_cartesian_tready : out std_logic;
    m_axis_dout_tdata : out std_logic_vector(7 downto 0);
    m_axis_dout_tvalid, m_axis_dout_tlast : out std_logic;
    m_axis_dout_tuser : out std_logic_vector(2 downto 0);
    m_axis_dout_tready : in std_logic
  );
end entity;

architecture fixture of dut_0 is
  signal toggle, extra : std_logic := '0';
begin
  process(aclk)
  begin
    if rising_edge(aclk) then
      if aresetn = '0' then
        toggle <= '0';
        extra <= '0';
      else
        toggle <= not toggle;
        if fault_mode = 5 and s_axis_cartesian_tvalid = '1' and
           m_axis_dout_tready = '1' and s_axis_cartesian_tdata = x"FF" then
          extra <= '1';
        elsif extra = '1' and m_axis_dout_tready = '1' then
          extra <= '0';
        end if;
      end if;
    end if;
  end process;
  s_axis_cartesian_tready <= m_axis_dout_tready and aresetn;
  m_axis_dout_tvalid <= '0' when fault_mode = 4 else
                       (s_axis_cartesian_tvalid or extra) and aresetn;
  m_axis_dout_tlast <= not s_axis_cartesian_tlast when fault_mode = 6 else s_axis_cartesian_tlast;
  m_axis_dout_tuser <= s_axis_cartesian_tuser xor "001" when fault_mode = 7 else s_axis_cartesian_tuser;
  process(all)
    variable value : std_logic_vector(7 downto 0);
  begin
    case to_integer(unsigned(s_axis_cartesian_tdata)) is
      when 0 => value := x"00";
      when 1 | 2 | 3 => value := x"01";
      when 4 | 7 | 8 => value := x"02";
      when 9 | 15 => value := x"03";
      when 16 => value := x"04";
      when 224 => value := x"0E";
      when 225 | 255 => value := x"0F";
      when others => value := (others => 'X');
    end case;
    if fault_mode = 1 and s_axis_cartesian_tdata = x"02" then
      value := x"02";
    elsif fault_mode = 2 then
      value(0) := 'X';
    elsif fault_mode = 3 then
      value(0) := value(0) xor toggle;
    elsif fault_mode = 8 then
      value(7) := '1';
    end if;
    m_axis_dout_tdata <= value;
  end process;
end architecture;

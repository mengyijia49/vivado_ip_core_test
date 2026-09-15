library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (
    aclk, aresetn : in std_logic;
    s_axis_a_tdata : in std_logic_vector(15 downto 0);
    s_axis_a_tvalid, s_axis_a_tlast : in std_logic;
    s_axis_a_tuser : in std_logic_vector(2 downto 0);
    s_axis_a_tready : out std_logic;
    m_axis_result_tdata : out std_logic_vector(7 downto 0);
    m_axis_result_tvalid, m_axis_result_tlast : out std_logic;
    m_axis_result_tuser : out std_logic_vector(4 downto 0);
    m_axis_result_tready : in std_logic
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
        if fault_mode = 5 and s_axis_a_tvalid = '1' and
           m_axis_result_tready = '1' and s_axis_a_tdata = x"0001" then
          extra <= '1';
        elsif extra = '1' and m_axis_result_tready = '1' then
          extra <= '0';
        end if;
      end if;
    end if;
  end process;
  s_axis_a_tready <= m_axis_result_tready and aresetn;
  m_axis_result_tvalid <= '0' when fault_mode = 4 else (s_axis_a_tvalid or extra) and aresetn;
  m_axis_result_tlast <= not s_axis_a_tlast when fault_mode = 6 else s_axis_a_tlast;
  process(all)
    variable value : std_logic_vector(7 downto 0);
    variable flags : std_logic_vector(1 downto 0);
    variable user : std_logic_vector(4 downto 0);
  begin
    flags := "00";
    case s_axis_a_tdata is
      when x"0000" | x"8000" | x"03FF" | x"0400" | x"0001" => value := x"00";
      when x"3C00" => value := x"01";
      when x"4100" => value := x"02";
      when x"4300" => value := x"04";
      when x"C100" => value := x"FE";
      when x"4780" => value := x"07"; flags := "01";
      when x"C840" => value := x"F8";
      when x"C880" => value := x"F8"; flags := "01";
      when x"7C00" => value := x"07"; flags := "11";
      when x"FC00" => value := x"F8"; flags := "11";
      when x"7C01" | x"7E00" | x"FC01" => value := x"F8"; flags := "10";
      when others => value := (others => 'X');
    end case;
    user := s_axis_a_tuser & flags;
    if fault_mode = 1 and s_axis_a_tdata = x"4100" then
      value := x"03";
    elsif fault_mode = 2 then
      value(0) := 'X';
    elsif fault_mode = 3 then
      value(0) := value(0) xor toggle;
    elsif fault_mode = 7 then
      user(2) := not user(2);
    elsif fault_mode = 8 then
      value(7) := not value(7);
    elsif fault_mode = 9 then
      user(0) := not user(0);
    elsif fault_mode = 10 and s_axis_a_tdata = x"7E00" then
      value := x"00";
    end if;
    m_axis_result_tdata <= value;
    m_axis_result_tuser <= user;
  end process;
end architecture;

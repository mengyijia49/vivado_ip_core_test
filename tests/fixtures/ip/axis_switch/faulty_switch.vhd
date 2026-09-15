library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (
    aclk, aresetn : in std_logic;
    s_axis_tvalid : in std_logic_vector(1 downto 0);
    s_axis_tready : out std_logic_vector(1 downto 0);
    s_axis_tdata : in std_logic_vector(15 downto 0);
    s_axis_tlast : in std_logic_vector(1 downto 0);
    s_axis_tid : in std_logic_vector(3 downto 0);
    s_axis_tdest : in std_logic_vector(1 downto 0);
    s_axis_tuser : in std_logic_vector(7 downto 0);
    s_decode_err : out std_logic_vector(1 downto 0);
    m_axis_tvalid : out std_logic_vector(1 downto 0);
    m_axis_tready : in std_logic_vector(1 downto 0);
    m_axis_tdata : out std_logic_vector(15 downto 0);
    m_axis_tlast : out std_logic_vector(1 downto 0);
    m_axis_tid : out std_logic_vector(3 downto 0);
    m_axis_tdest : out std_logic_vector(1 downto 0);
    m_axis_tuser : out std_logic_vector(7 downto 0)
  );
end entity;

architecture fixture of dut_0 is
  type words is array (0 to 1) of std_logic_vector(15 downto 0);
  type selections is array (0 to 1) of integer range -1 to 1;
  signal data : words := (others => (others => '0'));
  signal full : std_logic_vector(1 downto 0) := "00";
  signal selected : selections := (others => -1);
  signal changing : std_logic := '0';
begin
  process(all)
    variable chosen : selections;
    variable ready, valid : std_logic_vector(1 downto 0);
    variable word : std_logic_vector(15 downto 0);
    variable target : natural;
  begin
    chosen := (others => -1);
    ready := "00";
    valid := full;
    s_decode_err <= "00";
    for b in 0 to 1 loop
      if full(b) = '0' or m_axis_tready(b) = '1' then
        for s in 0 to 1 loop
          if chosen(b) = -1 and s_axis_tvalid(s) = '1' and
             to_integer(unsigned(s_axis_tdest(s downto s))) = b then
            chosen(b) := s;
            ready(s) := '1';
          end if;
        end loop;
      end if;
      word := data(b);
      target := b;
      case fault_mode is
        when 1 => target := 1-b;
        when 2 => word(15) := not word(15);
        when 3 => valid(b) := '0';
        when 5 => word(0) := not word(0);
        when 6 => valid(b) := 'X';
        when 7 => word(15) := word(15) xor changing;
        when 8 => word(8) := not word(8);
        when 9 => s_decode_err <= "11";
        when 10 => ready(0) := 'X';
        when 11 => word(7) := not word(7);
        when 12 => word(5) := not word(5);
        when 13 => ready(0) := '0';
        when others => null;
      end case;
      m_axis_tdata((target+1)*8-1 downto target*8) <= word(15 downto 8);
      m_axis_tlast(target) <= word(7);
      m_axis_tid((target+1)*2-1 downto target*2) <= word(6 downto 5);
      m_axis_tdest(target) <= word(4);
      m_axis_tuser((target+1)*4-1 downto target*4) <= word(3 downto 0);
    end loop;
    if fault_mode = 1 then
      valid := valid(0) & valid(1);
    end if;
    if aresetn = '0' then
      ready := "00";
      valid := "00";
      chosen := (others => -1);
      s_decode_err <= "00";
    end if;
    selected <= chosen;
    s_axis_tready <= ready;
    m_axis_tvalid <= valid;
  end process;

  process(aclk)
    variable s : natural;
  begin
    if rising_edge(aclk) then
      changing <= not changing;
      if aresetn = '0' then
        full <= "00";
      else
        for b in 0 to 1 loop
          if m_axis_tready(b) = '1' and fault_mode /= 4 then
            full(b) <= '0';
          end if;
          if selected(b) /= -1 then
            s := selected(b);
            data(b) <= s_axis_tdata((s+1)*8-1 downto s*8) & s_axis_tlast(s) &
                       s_axis_tid((s+1)*2-1 downto s*2) & s_axis_tdest(s) &
                       s_axis_tuser((s+1)*4-1 downto s*4);
            full(b) <= '1';
          end if;
        end loop;
      end if;
    end if;
  end process;
end architecture;

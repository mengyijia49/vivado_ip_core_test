library ieee;
use ieee.std_logic_1164.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (In0 : in std_logic_vector(0 downto 0);
        In1 : in std_logic_vector(2 downto 0);
        In2 : in std_logic_vector(3 downto 0);
        dout : out std_logic_vector(7 downto 0));
end entity;

architecture sim of dut_0 is
begin
  process(all)
    variable word : std_logic_vector(7 downto 0);
  begin
    word := In2 & In1 & In0;
    case fault_mode is
      when 1 => word := In0 & In1 & In2;
      when 2 => word(1 downto 0) := In0(0) & In1(0);
      when 3 => word(7) := '0';
      when 4 => word(0) := 'X';
      when 5 => word(6 downto 4) := "000";
      when others => null;
    end case;
    dout <= word;
  end process;
end architecture;

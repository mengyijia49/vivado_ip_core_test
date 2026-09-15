library ieee;
use ieee.std_logic_1164.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (Din : in std_logic_vector(7 downto 0);
        Dout : out std_logic_vector(3 downto 0));
end entity;

architecture sim of dut_0 is
begin
  process(all)
    variable word : std_logic_vector(3 downto 0);
  begin
    word := Din(5 downto 2);
    case fault_mode is
      when 1 => word := Din(6 downto 3);
      when 2 => word := Din(2) & Din(3) & Din(4) & Din(5);
      when 3 => word(0) := word(0) xor Din(7);
      when 4 => word(3) := 'X';
      when 5 => word(3) := '0';
      when others => null;
    end case;
    Dout <= word;
  end process;
end architecture;

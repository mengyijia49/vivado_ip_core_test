library ieee;
use ieee.std_logic_1164.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (dout : out std_logic_vector(4095 downto 0));
end entity;

architecture sim of dut_0 is
begin
  process
    variable word : std_logic_vector(4095 downto 0) := (4095 => '1', 0 => '1', others => '0');
  begin
    case fault_mode is
      when 1 => word(4095) := '0';
      when 2 => word(0) := '0';
      when 3 => word(2048) := 'X';
      when others => null;
    end case;
    dout <= word;
    wait for 300 ns;
    if fault_mode = 4 then
      word(4095) := '0';
      dout <= word;
    end if;
    wait;
  end process;
end architecture;

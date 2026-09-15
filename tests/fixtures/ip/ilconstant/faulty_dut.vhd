library ieee;
use ieee.std_logic_1164.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (dout : out std_logic_vector(4095 downto 0));
end entity;

architecture fixture of dut_0 is
  constant expected : std_logic_vector(4095 downto 0) := (4095 => '1', 0 => '1', others => '0');
begin
  correct : if fault_mode = 0 generate dout <= expected; end generate;
  lost_high : if fault_mode = 1 generate dout <= (0 => '1', others => '0'); end generate;
  late_change : if fault_mode = 2 generate
    process
    begin
      dout <= expected;
      wait for 300 ns;
      dout <= (others => '0');
      wait;
    end process;
  end generate;
  unknown_bit : if fault_mode = 3 generate
    dout <= (4095 => '1', 2048 => 'X', 0 => '1', others => '0');
  end generate;
end architecture;

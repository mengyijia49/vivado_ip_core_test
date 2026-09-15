library ieee;
use ieee.std_logic_1164.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (Din : in std_logic_vector(7 downto 0);
        Dout : out std_logic_vector(3 downto 0));
end entity;

architecture fixture of dut_0 is
begin
  correct : if fault_mode = 0 generate Dout <= Din(5 downto 2); end generate;
  wrong_offset : if fault_mode = 1 generate Dout <= Din(6 downto 3); end generate;
  leaked_high : if fault_mode = 2 generate Dout <= Din(7) & Din(4 downto 2); end generate;
  unknown_bit : if fault_mode = 3 generate Dout <= 'X' & Din(4 downto 2); end generate;
end architecture;

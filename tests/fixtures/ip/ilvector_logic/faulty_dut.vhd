library ieee;
use ieee.std_logic_1164.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (Op1, Op2 : in std_logic_vector(7 downto 0);
        Res : out std_logic_vector(7 downto 0));
end entity;

architecture fixture of dut_0 is
  signal correct_value : std_logic_vector(7 downto 0);
begin
  correct_value <= Op1 xor Op2;
  correct : if fault_mode = 0 generate Res <= correct_value; end generate;
  high_lost : if fault_mode = 1 generate Res <= '0' & correct_value(6 downto 0); end generate;
  wrong_operation : if fault_mode = 2 generate Res <= Op1 and Op2; end generate;
  shifted_input : if fault_mode = 3 generate Res <= Op1 xor (Op2(6 downto 0) & Op2(7)); end generate;
  unknown_bit : if fault_mode = 4 generate Res <= 'X' & correct_value(6 downto 0); end generate;
end architecture;

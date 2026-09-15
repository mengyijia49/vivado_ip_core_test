library ieee;
use ieee.std_logic_1164.all;

entity dut_0 is
  port (Op1, Op2 : in std_logic_vector(1 downto 0);
        Res : out std_logic_vector(1 downto 0));
end entity;

architecture fault_fixture of dut_0 is
begin
  Res <= 'X' & (Op1(0) xor Op2(0));
end architecture;

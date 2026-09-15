library ieee;
use ieee.std_logic_1164.all;

entity dut_0 is
  port (Op1 : in std_logic_vector(0 downto 0); Res : out std_logic);
end entity;

architecture faulty of dut_0 is
begin
  Res <= 'X';
end architecture;

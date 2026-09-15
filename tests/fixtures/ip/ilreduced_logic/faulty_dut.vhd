library ieee;
use ieee.std_logic_1164.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (Op1 : in std_logic_vector(16 downto 0); Res : out std_logic);
end entity;

architecture fixture of dut_0 is
  function parity(value : std_logic_vector) return std_logic is
    variable result : std_logic := '0';
  begin
    for i in value'range loop result := result xor value(i); end loop;
    return result;
  end;
begin
  correct : if fault_mode = 0 generate Res <= parity(Op1); end generate;
  high_lost : if fault_mode = 1 generate Res <= parity(Op1(15 downto 0)); end generate;
  wrong_operation : if fault_mode = 2 generate
    Res <= '1' when Op1 /= "00000000000000000" else '0';
  end generate;
  unknown_bit : if fault_mode = 3 generate Res <= 'X'; end generate;
end architecture;

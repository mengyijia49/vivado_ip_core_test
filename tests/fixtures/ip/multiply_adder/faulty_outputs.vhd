library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity dut_0 is
  port (A, B, C : in std_logic_vector(1 downto 0);
        SUBTRACT : in std_logic;
        P : out std_logic_vector(2 downto 0);
        PCOUT : out std_logic_vector(47 downto 0));
end entity;

architecture fault_fixture of dut_0 is
begin
  process (A, B, C, SUBTRACT)
    variable product, value : integer;
    variable correct, cascade, primary : std_logic_vector(47 downto 0);
  begin
    product := to_integer(unsigned(A)) * to_integer(unsigned(B));
    value := to_integer(unsigned(C)) + product;
    if SUBTRACT = '1' then
      value := to_integer(unsigned(C)) - product;
    end if;
    correct := std_logic_vector(to_signed(value, 48));
    primary := correct;
    cascade := correct;
    if SUBTRACT = '1' and C = "10" then
      cascade(8) := not cascade(8);
    elsif SUBTRACT = '1' and C = "11" then
      primary := std_logic_vector(to_signed(product - to_integer(unsigned(C)), 48));
    end if;
    P <= primary(2 downto 0);
    PCOUT <= cascade;
  end process;
end architecture;

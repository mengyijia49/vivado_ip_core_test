library ieee;
use ieee.std_logic_1164.all;

entity mult_gen_0 is
  port (
    CLK : in std_logic;
    A, B : in std_logic_vector(1 downto 0);
    P : out std_logic_vector(3 downto 0)
  );
end entity;

architecture injected of mult_gen_0 is
begin
  process(CLK)
  begin
    if rising_edge(CLK) then
      P <= (others => 'X');
    end if;
  end process;
end architecture;

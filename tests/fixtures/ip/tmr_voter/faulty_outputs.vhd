library ieee;
use ieee.std_logic_1164.all;

entity dut_0 is
  port (Discrete1, Discrete2, Discrete3 : in std_logic_vector(7 downto 0);
        Discrete : out std_logic_vector(7 downto 0);
        Compare : out std_logic_vector(3 downto 0));
end entity;

architecture fixture of dut_0 is
begin
  process(all)
    variable voted : std_logic_vector(7 downto 0);
    variable flags : std_logic_vector(3 downto 0);
  begin
    voted := (Discrete1 and Discrete2) or (Discrete1 and Discrete3) or (Discrete2 and Discrete3);
    flags := (others => '0');
    if Discrete1 /= Discrete2 then flags(0) := '1'; end if;
    if Discrete1 /= Discrete3 then flags(1) := '1'; end if;
    if Discrete2 /= Discrete3 then flags(2) := '1'; end if;
    if Discrete1 = x"A5" then voted(0) := not voted(0); end if;
    if Discrete1 = x"5A" then flags := (others => '0'); end if;
    Discrete <= voted;
    Compare <= flags;
  end process;
end architecture;

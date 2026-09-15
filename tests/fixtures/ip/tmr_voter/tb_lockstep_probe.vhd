library ieee;
use ieee.std_logic_1164.all;

entity tb_lockstep_probe is
end entity;

architecture test of tb_lockstep_probe is
  signal a, b, voted : std_logic_vector(0 downto 0) := "0";
  signal flags : std_logic_vector(3 downto 0);
begin
  dut : entity work.dut_0
    port map (Discrete1 => a, Discrete2 => b, Discrete => voted, Compare => flags);
  process
  begin
    a <= "1";
    b <= "0";
    wait for 1 ns;
    assert voted = "1" and flags(0) = '1'
      report "TMR_LOCKSTEP_PROBE: FAIL" severity failure;
    report "TMR_LOCKSTEP_PROBE: PASS";
    std.env.finish;
    wait;
  end process;
end architecture;

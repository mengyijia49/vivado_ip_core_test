library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;

entity tb_optional_strb is end entity;
architecture sim of tb_optional_strb is
  constant HAS_STRB : boolean := $has_strb;
  signal clk : std_logic := '0';
  signal rstn, valid, ready : std_logic := '0';
  signal keep, strb : std_logic_vector(0 downto 0) := "0";
  signal status : std_logic_vector(31 downto 0);
  signal asserted : std_logic;
begin
  clk <= not clk after 5 ns;
  dut : entity work.dut_0 port map (
    aclk => clk, aresetn => rstn,
    pc_axis_tvalid => valid, pc_axis_tready => ready,
    pc_axis_tdata => x"00", pc_axis_tkeep => keep,
    pc_status => status, pc_asserted => asserted$strb_mapping);

  stimulus : process
    procedure tick is
    begin
      wait until rising_edge(clk);
      wait until falling_edge(clk);
    end procedure;
    procedure probe(scenario : natural; expected : natural) is
    begin
      rstn <= '0'; valid <= '0'; ready <= '0'; keep <= "0"; strb <= "0";
      for i in 1 to 4 loop tick; end loop;
      rstn <= '1';
      for i in 1 to 6 loop tick; end loop;
      if scenario = 3 then keep <= "1"; end if;
      valid <= '1';
      tick; tick;
      case scenario is
        when 1 => keep <= "1";
        when 2 => keep <= "1"; strb <= "1";
        when 3 => strb <= "1";
        when others => null;
      end case;
      tick; tick;
      ready <= '1'; tick;
      valid <= '0';
      for i in 1 to 8 loop tick; end loop;
      report "OPTIONAL_STRB scenario=" & integer'image(scenario) &
             " expected=" & to_hstring(std_logic_vector(to_unsigned(expected, 32))) &
             " actual=" & to_hstring(status);
      assert status = std_logic_vector(to_unsigned(expected, 32))
        report "OPTIONAL_STRB_STATUS: FAIL status" severity failure;
      if expected = 0 then
        assert asserted = '0' report "OPTIONAL_STRB_STATUS: FAIL asserted" severity failure;
      else
        assert asserted = '1' report "OPTIONAL_STRB_STATUS: FAIL asserted" severity failure;
      end if;
    end procedure;
  begin
    probe(0, 0);
    if HAS_STRB then probe(1, 16#08#); else probe(1, 16#48#); end if;
    probe(2, 16#48#);
    if HAS_STRB then probe(3, 16#40#); else probe(3, 0); end if;
    report "OPTIONAL_STRB_STATUS: PASS";
    finish;
  end process;
  watchdog : process
  begin
    wait for 10 us;
    assert false report "OPTIONAL_STRB_STATUS: FAIL timeout" severity failure;
  end process;
end architecture;

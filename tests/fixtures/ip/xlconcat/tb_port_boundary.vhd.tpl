library ieee;
use ieee.std_logic_1164.all;
use std.env.all;

entity tb_port_boundary is
end entity;

architecture sim of tb_port_boundary is
  signal stimulus, actual : std_logic_vector($last downto 0) := (others => '0');
begin
  dut : entity work.dut_0
    port map (
$mappings,
      dout => actual
    );

  exercise : process
    variable word : std_logic_vector(stimulus'range);
    variable mismatches : natural := 0;
    procedure observe(name : string; expected : std_logic_vector) is
    begin
      report "CONCAT_PORT_OBSERVATION " & name & " expected=" & to_string(expected) &
             " actual=" & to_string(actual);
      if is_x(actual) or actual /= expected then
        mismatches := mismatches + 1;
      end if;
    end procedure;
  begin
    wait for 1 us;
    word := (others => '0');
    observe("zero", word);
    word := (others => '1');
    stimulus <= word;
    wait for 1 us;
    observe("ones", word);
    wait for 5 us;
    observe("ones_late", word);
    word := (word'high => '1', others => '0');
    stimulus <= word;
    wait for 1 us;
    observe("high", word);
    word := (0 => '1', others => '0');
    stimulus <= word;
    wait for 1 us;
    observe("low", word);
    for bit in word'range loop
      if bit mod 2 = 0 then word(bit) := '1'; else word(bit) := '0'; end if;
    end loop;
    stimulus <= word;
    wait for 1 us;
    observe("alternating", word);
    report "CONCAT_PORT_MISMATCHES " & integer'image(mismatches);
    report "CONCAT_PORT_PROBE: COMPLETE";
    finish;
    wait;
  end process;
end architecture;

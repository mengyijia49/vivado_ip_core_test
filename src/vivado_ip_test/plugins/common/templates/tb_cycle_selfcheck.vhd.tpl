library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_textio.all;
use std.textio.all;
use std.env.all;

entity tb_cycle_selfcheck is
end entity;

architecture sim of tb_cycle_selfcheck is
  signal clk : std_logic := '0';
$signals
begin
  dut : entity work.dut_0
    port map (
      $mappings
    );

  stimulus_and_checker : process
    file inputs : text open read_mode is "$input_path";
    file expected_file : text open read_mode is "$expected_path";
    file actual_file : text open write_mode is "$actual_path";
$mask_declaration
    variable input_line, expected_line, output_line, mask_line : line;
$stimulus_declaration
    variable expected, actual : std_logic_vector($output_width - 1 downto 0);
    variable expected_mask : std_logic_vector($output_width - 1 downto 0) := (others => '1');
    variable count : natural := 0;
    -- The framework writes one complete binary word per line.
    procedure read_binary(variable text_line : in line; variable value : out std_logic_vector) is
      alias bits : std_logic_vector(1 to value'length) is value;
    begin
      assert text_line /= null
        report "CYCLE_SELF_CHECK_STATUS: FAIL missing binary row" severity failure;
      assert text_line.all'length = value'length
        report "CYCLE_SELF_CHECK_STATUS: FAIL binary row width" severity failure;
      for index in bits'range loop
        case text_line.all(text_line.all'low + index - 1) is
          when '0' => bits(index) := '0';
          when '1' => bits(index) := '1';
          when others =>
            assert false report "CYCLE_SELF_CHECK_STATUS: FAIL nonbinary row" severity failure;
        end case;
      end loop;
    end procedure;
  begin
    wait for 200 ns;
    while not endfile(inputs) loop
      assert not endfile(expected_file)
        report "CYCLE_SELF_CHECK_STATUS: FAIL missing expected row" severity failure;
      readline(inputs, input_line);
$stimulus_read
      readline(expected_file, expected_line);
      read_binary(expected_line, expected);
$mask_read
$assignments
      wait for 5 ns;
      clk <= '1';
      wait for 1 ns;
$captures
      write(output_line, actual);
      writeline(actual_file, output_line);
      flush(actual_file);
      assert $comparison
        report "CYCLE_SELF_CHECK_STATUS: FAIL cycle=" & integer'image(count) &
               " expected=" & to_string(expected) & " actual=" & to_string(actual)
        severity failure;
      count := count + 1;
      wait for 4 ns;
      clk <= '0';
    end loop;
    assert count = $count and count > 0 and endfile(expected_file)$mask_end
      report "CYCLE_SELF_CHECK_STATUS: FAIL row count" severity failure;
    report "CYCLE_SELF_CHECK_STATUS: PASS";
    finish;
    wait;
  end process;

  watchdog : process
  begin
    wait for $timeout_ns ns;
    assert false report "CYCLE_SELF_CHECK_STATUS: FAIL timeout" severity failure;
    wait;
  end process;
end architecture;

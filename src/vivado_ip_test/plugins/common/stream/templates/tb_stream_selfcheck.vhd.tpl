library ieee;
use ieee.std_logic_1164.all;
use ieee.std_logic_textio.all;
use std.textio.all;
use std.env.all;

entity tb_stream_selfcheck is
end entity;

architecture sim of tb_stream_selfcheck is
  constant count : positive := $count;
  signal s_clk, m_clk : std_logic := '0';
  signal resetn : std_logic := '0';
  signal s_valid, s_ready, m_valid, m_ready : std_logic := '0';
  signal sent, source_stalls : natural := 0;
  signal source_done : boolean := false;
$signals
begin
  s_clk <= not s_clk after 5 ns;
  $output_clock
  resetn <= '1' after 200 ns;
  dut : entity work.dut_0
    port map (
      $mappings
    );

  source_driver : process
    file inputs : text open read_mode is "$input_vectors_path";
    file gaps : text open read_mode is "$gaps_path";
    file accepted : text open write_mode is "$accepted_input_path";
    variable row, gap_row, output_row : line;
    variable stimulus : std_logic_vector($width - 1 downto 0);
    variable gap : natural;
    variable accepted_count, stalls : natural := 0;
  begin
    wait until resetn = '1';
    wait until falling_edge(s_clk);
    while not endfile(inputs) loop
      assert not endfile(gaps)
        report "AXIS_SELF_CHECK_STATUS: FAIL missing input gap" severity failure;
      readline(inputs, row);
      read(row, stimulus);
      readline(gaps, gap_row);
      read(gap_row, gap);
      for i in 1 to gap loop
        wait until falling_edge(s_clk);
      end loop;
$assignments
      s_valid <= '1';
      loop
        wait until rising_edge(s_clk);
        assert s_ready = '0' or s_ready = '1'
          report "AXIS_SELF_CHECK_STATUS: FAIL unknown input ready" severity failure;
        exit when s_ready = '1';
        stalls := stalls + 1;
        source_stalls <= stalls;
      end loop;
      write(output_row, stimulus);
      writeline(accepted, output_row);
      flush(accepted);
      accepted_count := accepted_count + 1;
      sent <= accepted_count;
      wait until falling_edge(s_clk);
      s_valid <= '0';
    end loop;
    assert endfile(gaps) and accepted_count = count
      report "AXIS_SELF_CHECK_STATUS: FAIL input count" severity failure;
    source_done <= true;
    wait;
  end process;

  sink_driver : process
    file pattern : text open read_mode is "$ready_path";
    variable row : line;
    variable bit_value : std_logic;
  begin
    wait until resetn = '1';
    for i in 1 to $initial_stall loop
      wait until falling_edge(m_clk);
    end loop;
    loop
      if endfile(pattern) then
        file_close(pattern);
        file_open(pattern, "$ready_path", read_mode);
      end if;
      readline(pattern, row);
      read(row, bit_value);
      m_ready <= bit_value;
      wait until falling_edge(m_clk);
    end loop;
  end process;

$scoreboard

  watchdog : process
  begin
    wait for $timeout_ns ns;
    assert false report "AXIS_SELF_CHECK_STATUS: FAIL watchdog timeout" severity failure;
    wait;
  end process;
end architecture;

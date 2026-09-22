library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;

entity tb_dds_phase_probe is
end entity;

architecture sim of tb_dds_phase_probe is
  signal clk : std_logic := '0';
  signal resetn : std_logic := '0';
  signal phase_valid : std_logic;
  signal phase_ready : std_logic := '1';
  signal phase_data : std_logic_vector(7 downto 0);
begin
  clk <= not clk after 5 ns;

  dut : entity work.probe_0
    port map (
      aclk => clk,
      aresetn => resetn,
      m_axis_phase_tvalid => phase_valid,
      m_axis_phase_tready => phase_ready,
      m_axis_phase_tdata => phase_data
    );

  process
  begin
    for cycle in 0 to 39 loop
      wait until falling_edge(clk);
      if cycle = 3 then
        resetn <= '1';
      end if;
      if cycle = 10 then
        phase_ready <= '0';
      elsif cycle = 14 then
        phase_ready <= '1';
      end if;
      if cycle = 18 then
        resetn <= '0';
      elsif cycle = 22 then
        resetn <= '1';
      elsif cycle = 26 then
        phase_ready <= '0';
      elsif cycle = 28 then
        resetn <= '0';
      elsif cycle = 32 then
        resetn <= '1';
      elsif cycle = 34 then
        phase_ready <= '1';
      end if;
      report "DDS_PHASE_SAMPLE cycle=" & integer'image(cycle) &
             " resetn=" & std_logic'image(resetn) &
             " ready=" & std_logic'image(phase_ready) &
             " valid=" & std_logic'image(phase_valid) &
             " data=" & integer'image(to_integer(unsigned(phase_data)));
    end loop;
    report "DDS_PHASE_PROBE_STATUS: PASS";
    finish;
    wait;
  end process;
end architecture;

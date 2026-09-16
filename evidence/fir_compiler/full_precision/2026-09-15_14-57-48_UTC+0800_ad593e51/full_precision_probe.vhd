library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;

entity tb_fir_full_precision_probe is
end entity;

architecture sim of tb_fir_full_precision_probe is
  constant kind : natural := 0;
  type values_t is array(0 to 15) of integer;
  type tables_t is array(0 to 2) of values_t;
  constant inputs : values_t := (0, -128, -128, -128, 127, -127, 0, 1, -1, 64, -64, 0, 0, 0, 0, 0);
  -- Literal results for [-8,0,0], [-1,-1,-2], and [1,1,2], respectively.
  constant expected : tables_t := (
    (0, 1024, 1024, 1024, -1016, 1016, 0, -8, 8, -512, 512, 0, 0, 0, 0, 0),
    (0, 128, 256, 512, 257, 256, -127, 253, 0, -65, 2, -64, 128, 0, 0, 0),
    (0, -128, -256, -512, -257, -256, 127, -253, 0, 65, -2, 64, -128, 0, 0, 0));
  signal clk : std_logic := '0';
  signal resetn, source_valid, source_ready, source_last : std_logic := '0';
  signal sink_valid, sink_ready, sink_last : std_logic := '0';
  signal source_data : std_logic_vector(7 downto 0) := (others => '0');
  signal source_user, sink_user : std_logic_vector(6 downto 0) := (others => '0');
  signal sink_data : std_logic_vector(15 downto 0);
  signal accepted : natural := 0;
begin
  clk <= not clk after 5 ns;
  resetn <= '1' after 200 ns;
  dut : entity work.probe_0
    port map (aclk => clk, aresetn => resetn,
      s_axis_data_tdata => source_data, s_axis_data_tuser => source_user,
      s_axis_data_tlast => source_last, s_axis_data_tvalid => source_valid,
      s_axis_data_tready => source_ready, m_axis_data_tdata => sink_data,
      m_axis_data_tuser => sink_user, m_axis_data_tlast => sink_last,
      m_axis_data_tvalid => sink_valid, m_axis_data_tready => sink_ready);
  process
  begin
    wait until resetn = '1';
    for i in inputs'range loop
      for delay in 0 to i mod 3 loop
        wait until falling_edge(clk);
      end loop;
      source_data <= std_logic_vector(to_signed(inputs(i), 8));
      source_user <= std_logic_vector(to_unsigned(i * 7, 7));
      if i mod 4 = 3 then source_last <= '1'; else source_last <= '0'; end if;
      source_valid <= '1';
      loop
        wait until rising_edge(clk);
        assert source_ready = '0' or source_ready = '1'
          report "FIR_FULL_PRECISION_STATUS: FAIL unknown input ready" severity failure;
        exit when source_ready = '1';
      end loop;
      accepted <= accepted + 1;
      wait until falling_edge(clk);
      source_valid <= '0';
    end loop;
    wait;
  end process;
  process
    variable cycle : natural := 0;
  begin
    wait until resetn = '1';
    loop
      wait until falling_edge(clk);
      cycle := cycle + 1;
      if cycle < 60 or cycle mod 5 < 2 then sink_ready <= '0';
      else sink_ready <= '1'; end if;
    end loop;
  end process;
  process
    variable count, tail, failures : natural := 0;
    variable ending : std_logic;
    variable stalled : boolean := false;
    variable held : std_logic_vector(23 downto 0);
  begin
    wait until resetn = '1';
    loop
      wait until rising_edge(clk);
      assert sink_valid = '0' or sink_valid = '1'
        report "FIR_FULL_PRECISION_STATUS: FAIL unknown valid" severity failure;
      if stalled then
        assert sink_valid = '1' and (sink_data & sink_user & sink_last) = held
          report "FIR_FULL_PRECISION_STATUS: FAIL changed under backpressure" severity failure;
      end if;
      stalled := sink_valid = '1' and sink_ready = '0';
      held := sink_data & sink_user & sink_last;
      if sink_valid = '1' and sink_ready = '1' then
        assert count < inputs'length
          report "FIR_FULL_PRECISION_STATUS: FAIL extra output" severity failure;
        assert not is_x(sink_data & sink_user & sink_last)
          report "FIR_FULL_PRECISION_STATUS: FAIL unknown payload" severity failure;
        if count mod 4 = 3 then ending := '1'; else ending := '0'; end if;
        assert sink_user = std_logic_vector(to_unsigned(count * 7, 7)) and sink_last = ending
          report "FIR_FULL_PRECISION_STATUS: FAIL sideband mismatch" severity failure;
        report "FIR_FULL_PRECISION_SAMPLE " & integer'image(count) &
               " expected=" & integer'image(expected(kind)(count)) &
               " actual=" & integer'image(to_integer(signed(sink_data))) severity note;
        if sink_data /= std_logic_vector(to_signed(expected(kind)(count), 16)) then
          failures := failures + 1;
        end if;
        wait for 0 ns;
        assert count < accepted
          report "FIR_FULL_PRECISION_STATUS: FAIL before accepted input" severity failure;
        count := count + 1;
      end if;
      if count = inputs'length then
        tail := tail + 1;
        exit when tail = 128;
      end if;
    end loop;
    assert failures = 0 report "FIR_FULL_PRECISION_STATUS: FAIL numeric differences=" &
      integer'image(failures) severity failure;
    report "FIR_FULL_PRECISION_STATUS: PASS" severity note;
    finish;
    wait;
  end process;
  process
  begin
    wait for 100 us;
    assert false report "FIR_FULL_PRECISION_STATUS: FAIL timeout" severity failure;
    wait;
  end process;
end architecture;

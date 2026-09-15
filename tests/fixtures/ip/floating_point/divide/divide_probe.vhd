library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;

entity tb_floating_divide_probe is
end entity;

architecture sim of tb_floating_divide_probe is
  type words_t is array(0 to 15) of std_logic_vector(31 downto 0);
  type lanes_t is array(0 to 1) of words_t;
  constant inputs : lanes_t := (
    (x"3F800000", x"3F800000", x"3F800000", x"BF800000",
     x"3F800000", x"00000000", x"7F800000", x"7F800000",
     x"00000000", x"00800000", x"7F7FFFFF", x"80000001",
     x"3F800000", x"7F800001", x"3F800000", x"40000000"),
    (x"40400000", x"40E00000", x"00000000", x"00000000",
     x"80000000", x"00000000", x"7F800000", x"00000000",
     x"BF800000", x"40000000", x"3F000000", x"3F800000",
     x"80000001", x"00000000", x"FF800000", x"3FC00000"));
  constant expected : words_t := (
    x"3EAAAAAB", x"3E124925", x"7F800000", x"FF800000",
    x"FF800000", x"7FC00000", x"7FC00000", x"7F800000",
    x"80000000", x"00000000", x"7F800000", x"80000000",
    x"FF800000", x"7FC00000", x"80000000", x"3FAAAAAB");
  type flags_t is array(0 to 15) of std_logic_vector(3 downto 0);
  constant flags : flags_t := (2 | 3 | 4 | 12 => "1000", 5 | 6 => "0100",
                              9 => "0001", 10 => "0010", others => "0000");
  type source_words_t is array(0 to 1) of std_logic_vector(31 downto 0);
  type counts_t is array(0 to 1) of natural;
  signal clk : std_logic := '0';
  signal resetn, sink_valid, sink_ready, sink_last : std_logic := '0';
  signal valid, ready, last : std_logic_vector(0 to 1) := (others => '0');
  signal data, users : source_words_t := (others => (others => '0'));
  signal accepted : counts_t := (others => 0);
  signal sink_data : std_logic_vector(31 downto 0);
  signal sink_user : std_logic_vector(11 downto 0);
begin
  clk <= not clk after 5 ns;
  resetn <= '1' after 200 ns;
  dut : entity work.dut_0
    port map (aclk => clk, aresetn => resetn,
      s_axis_a_tdata => data(0), s_axis_a_tvalid => valid(0), s_axis_a_tready => ready(0),
      s_axis_a_tuser => users(0)(2 downto 0), s_axis_a_tlast => last(0),
      s_axis_b_tdata => data(1), s_axis_b_tvalid => valid(1), s_axis_b_tready => ready(1),
      s_axis_b_tuser => users(1)(4 downto 0), s_axis_b_tlast => last(1),
      m_axis_result_tdata => sink_data,
      m_axis_result_tvalid => sink_valid, m_axis_result_tready => sink_ready,
      m_axis_result_tlast => sink_last, m_axis_result_tuser => sink_user);
  sources : for lane in 0 to 1 generate
    process
      variable tag : natural;
    begin
      wait until resetn = '1';
      for delay in 1 to lane * 30 loop
        wait until rising_edge(clk);
      end loop;
      for i in expected'range loop
        wait until falling_edge(clk);
        data(lane) <= inputs(lane)(i);
        if lane = 0 then tag := i mod 8;
        else tag := (3 * i) mod 32;
        end if;
        users(lane) <= std_logic_vector(to_unsigned(tag, 32));
        if (i / (2 ** lane)) mod 2 = 0 then last(lane) <= '0';
        else last(lane) <= '1'; end if;
        valid(lane) <= '1';
        loop
          wait until rising_edge(clk);
          assert ready(lane) = '0' or ready(lane) = '1'
            report "FLOATING_DIVIDE_PROBE_STATUS: FAIL unknown input ready" severity failure;
          exit when ready(lane) = '1';
        end loop;
        accepted(lane) <= accepted(lane) + 1;
      end loop;
      wait until falling_edge(clk);
      valid(lane) <= '0';
      wait;
    end process;
  end generate;
  process
    variable cycle : natural := 0;
  begin
    wait until resetn = '1';
    loop
      wait until falling_edge(clk);
      cycle := cycle + 1;
      if cycle < 100 or cycle mod 7 < 3 then sink_ready <= '0';
      else sink_ready <= '1'; end if;
    end loop;
  end process;
  process
    variable count, tail, tag : natural := 0;
    variable ending : std_logic;
    variable stalled : boolean := false;
    variable held : std_logic_vector(44 downto 0);
  begin
    wait until resetn = '1';
    loop
      wait until rising_edge(clk);
      assert sink_valid = '0' or sink_valid = '1'
        report "FLOATING_DIVIDE_PROBE_STATUS: FAIL unknown valid" severity failure;
      if stalled then
        assert sink_valid = '1' and (sink_data & sink_user & sink_last) = held
          report "FLOATING_DIVIDE_PROBE_STATUS: FAIL changed under backpressure" severity failure;
      end if;
      stalled := sink_valid = '1' and sink_ready = '0';
      held := sink_data & sink_user & sink_last;
      if sink_valid = '1' and sink_ready = '1' then
        assert count < expected'length
          report "FLOATING_DIVIDE_PROBE_STATUS: FAIL extra output" severity failure;
        tag := count mod 8 + ((3 * count) mod 32) * 8;
        if count mod 4 = 0 then ending := '0'; else ending := '1'; end if;
        assert sink_data = expected(count) and sink_user = (std_logic_vector(to_unsigned(tag, 8)) & flags(count))
          and sink_last = ending
          report "FLOATING_DIVIDE_PROBE_STATUS: FAIL sample " & integer'image(count) severity failure;
        wait for 0 ns;
        assert count < accepted(0) and count < accepted(1)
          report "FLOATING_DIVIDE_PROBE_STATUS: FAIL result before accepted operands" severity failure;
        report "FLOATING_DIVIDE_SAMPLE " & integer'image(count) & " PASS" severity note;
        count := count + 1;
      end if;
      if count = expected'length then
        tail := tail + 1;
        exit when tail = 128;
      end if;
    end loop;
    report "FLOATING_DIVIDE_PROBE_STATUS: PASS" severity note;
    finish;
    wait;
  end process;
  process
  begin
    wait for 100 us;
    assert false report "FLOATING_DIVIDE_PROBE_STATUS: FAIL timeout" severity failure;
    wait;
  end process;
end architecture;

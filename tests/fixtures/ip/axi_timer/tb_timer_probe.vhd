library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;

entity tb_timer_probe is
end entity;

architecture sim of tb_timer_probe is
  signal clk, resetn : std_logic := '0';
  signal freeze : std_logic := '1';
  signal capture0, capture1 : std_logic := '0';
  signal generate0, generate1, pwm, irq : std_logic;
  signal awaddr, araddr : std_logic_vector(4 downto 0) := (others => '0');
  signal wdata, rdata : std_logic_vector(31 downto 0) := (others => '0');
  signal wstrb : std_logic_vector(3 downto 0) := (others => '1');
  signal awvalid, awready, wvalid, wready, bvalid, bready : std_logic := '0';
  signal arvalid, arready, rvalid, rready : std_logic := '0';
  signal bresp, rresp : std_logic_vector(1 downto 0);
  signal pulse0, pulse1 : natural := 0;
begin
  clk <= not clk after 5 ns;
  dut : entity work.probe_0
    port map (
      s_axi_aclk => clk, s_axi_aresetn => resetn,
      s_axi_awaddr => awaddr, s_axi_awvalid => awvalid, s_axi_awready => awready,
      s_axi_wdata => wdata, s_axi_wstrb => wstrb, s_axi_wvalid => wvalid, s_axi_wready => wready,
      s_axi_bresp => bresp, s_axi_bvalid => bvalid, s_axi_bready => bready,
      s_axi_araddr => araddr, s_axi_arvalid => arvalid, s_axi_arready => arready,
      s_axi_rdata => rdata, s_axi_rresp => rresp, s_axi_rvalid => rvalid, s_axi_rready => rready,
      capturetrig0 => capture0, capturetrig1 => capture1, freeze => freeze,
      generateout0 => generate0, generateout1 => generate1, pwm0 => pwm, interrupt => irq);

  monitor : process
    variable cycle : natural := 0;
  begin
    loop
      wait until rising_edge(clk);
      cycle := cycle + 1;
      wait for 1 ps;
      if resetn = '1' then
        assert not is_x(std_logic_vector'(generate0 & generate1 & pwm & irq))
          report "TIMER_PROBE: FAIL unknown side output" severity failure;
        if generate0 = '1' then
          pulse0 <= pulse0 + 1;
          report "TIMER_PULSE channel=0 cycle=" & integer'image(cycle);
        end if;
        if generate1 = '1' then
          pulse1 <= pulse1 + 1;
          report "TIMER_PULSE channel=1 cycle=" & integer'image(cycle);
        end if;
      end if;
    end loop;
  end process;

  stimulus : process
    procedure settle(n : natural := 64) is
    begin
      for i in 1 to n loop wait until falling_edge(clk); end loop;
    end procedure;

    procedure wr(address : natural; value : natural; strobe : natural := 15) is
      variable a_done, w_done : boolean := false;
    begin
      wait until falling_edge(clk);
      awaddr <= std_logic_vector(to_unsigned(address, 5));
      wdata <= std_logic_vector(to_unsigned(value, 32));
      wstrb <= std_logic_vector(to_unsigned(strobe, 4));
      awvalid <= '1'; wvalid <= '1';
      for cycle in 1 to 512 loop
        wait until rising_edge(clk);
        if awvalid = '1' and awready = '1' then a_done := true; end if;
        if wvalid = '1' and wready = '1' then w_done := true; end if;
        wait until falling_edge(clk);
        if a_done then awvalid <= '0'; end if;
        if w_done then wvalid <= '0'; end if;
        exit when a_done and w_done;
      end loop;
      assert a_done and w_done report "TIMER_PROBE: FAIL write request timeout" severity failure;
      bready <= '1';
      for cycle in 1 to 512 loop
        wait until rising_edge(clk);
        exit when bvalid = '1';
      end loop;
      assert bvalid = '1' and bresp = "00" report "TIMER_PROBE: FAIL write response" severity failure;
      wait until falling_edge(clk); bready <= '0';
      settle;
    end procedure;

    procedure rd(address : natural; label_text : string; variable value : out natural) is
    begin
      wait until falling_edge(clk);
      araddr <= std_logic_vector(to_unsigned(address, 5)); arvalid <= '1';
      for cycle in 1 to 512 loop
        wait until rising_edge(clk);
        exit when arready = '1';
      end loop;
      assert arready = '1' report "TIMER_PROBE: FAIL read request timeout" severity failure;
      wait until falling_edge(clk); arvalid <= '0'; rready <= '1';
      for cycle in 1 to 512 loop
        wait until rising_edge(clk);
        exit when rvalid = '1';
      end loop;
      assert rvalid = '1' and rresp = "00" and not is_x(rdata)
        report "TIMER_PROBE: FAIL read response" severity failure;
      value := to_integer(unsigned(rdata));
      report "TIMER_OBSERVATION " & label_text & "=" & to_hstring(rdata) &
        " irq=" & std_logic'image(irq) & " pulse0=" & integer'image(pulse0) &
        " pulse1=" & integer'image(pulse1);
      wait until falling_edge(clk); rready <= '0';
      settle;
    end procedure;

    procedure window(n : natural) is
    begin
      wait until falling_edge(clk);
      freeze <= '0'; settle(n); freeze <= '1'; settle;
    end procedure;

    variable value : natural;
  begin
    settle; resetn <= '1'; settle;
    rd(0, "reset_control0", value);
    assert value = 0 report "TIMER_PROBE: FAIL control reset" severity failure;
    rd(8, "reset_count0", value);
    assert value = 0 report "TIMER_PROBE: FAIL counter reset" severity failure;
    wr(4, 16#A5#, 0); rd(4, "zero_strobe_load", value);
    assert value = 16#A5# report "TIMER_PROBE: FAIL WSTRB must be ignored" severity failure;
    wr(0, 16#20#); rd(8, "explicit_load", value);
    assert value = 16#A5# report "TIMER_PROBE: FAIL load" severity failure;
    wr(0, 16#80#);
    for n in 1 to 4 loop
      window(n); rd(8, "linear_" & integer'image(n), value);
      assert value = 16#A5# + n*(n+1)/2
        report "TIMER_PROBE: FAIL fixed count window" severity failure;
    end loop;
    settle(256); rd(8, "freeze_hold", value);
    assert value = 175 report "TIMER_PROBE: FAIL freeze hold" severity failure;
    wr(0, 0); window(16); rd(8, "disabled_hold", value);
    assert value = 175 report "TIMER_PROBE: FAIL ENT hold" severity failure;
    wr(8, 17); rd(8, "readonly_count", value);
    assert value = 175 report "TIMER_PROBE: FAIL TCR must be read only" severity failure;
    wr(12, 123); rd(12, "reserved", value);
    assert value = 0 report "TIMER_PROBE: FAIL reserved register" severity failure;

    -- Observe rollover phase without deriving an oracle from the DUT.
    for reload in 0 to 1 loop
      wr(0, 16#120#); wr(4, 3); wr(0, 16#20#);
      wr(0, 16#C6# + reload*16);
      for n in 1 to 8 loop
        window(1); rd(8, "down_" & integer'image(reload) & "_" & integer'image(n), value);
        rd(0, "down_status_" & integer'image(reload) & "_" & integer'image(n), value);
      end loop;
      window(32); rd(8, "down_long_" & integer'image(reload), value);
      wr(0, 16#186# + reload*16); rd(0, "clear_irq_" & integer'image(reload), value);
      window(2); rd(8, "after_clear_" & integer'image(reload), value);
    end loop;
    wr(0, 16#120#); wr(4, 252); wr(0, 16#20#); wr(0, 16#D4#);
    for n in 1 to 8 loop
      window(1); rd(8, "up_reload_" & integer'image(n), value);
    end loop;

    wr(0, 16#120#); wr(4, 64); wr(0, 16#20#); wr(0, 16#C9#);
    rd(4, "capture_prime", value);
    capture0 <= '1'; settle(4); capture0 <= '0'; settle;
    rd(0, "capture_status", value);
    window(7);
    capture0 <= '1'; settle(4); capture0 <= '0'; settle;
    rd(4, "capture_value", value);
    capture0 <= '1'; settle(4); capture0 <= '0'; settle;
    rd(4, "capture_rearmed", value);
    wr(0, 16#189#); rd(0, "capture_irq_cleared", value);

    wr(0, 16#120#); wr(4, 10); wr(0, 16#20#); wr(0, 0);
    wr(16, 16#120#); wr(20, 20); wr(16, 16#20#); wr(16, 0);
    wr(0, 16#400#); rd(0, "enall0", value); rd(16, "enall1", value);
    window(7); rd(8, "enall_count0", value); rd(24, "enall_count1", value);
    wr(0, 16#80#); rd(0, "enall_clear0", value); rd(16, "enall_clear1", value);
    report "TIMER_PROBE: COMPLETE";
    finish;
    wait;
  end process;

  watchdog : process
  begin
    wait for 1 ms;
    assert false report "TIMER_PROBE: FAIL watchdog" severity failure;
    wait;
  end process;
end architecture;

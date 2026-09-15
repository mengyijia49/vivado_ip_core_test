library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;

entity tb_intc_probe is
end entity;

architecture sim of tb_intc_probe is
  signal clk, resetn : std_logic := '0';
  signal intr : std_logic_vector(3 downto 0) := "1100";
  signal irq : std_logic;
  signal awaddr, araddr : std_logic_vector(8 downto 0) := (others => '0');
  signal wdata, rdata : std_logic_vector(31 downto 0) := (others => '0');
  signal wstrb : std_logic_vector(3 downto 0) := (others => '1');
  signal awvalid, awready, wvalid, wready, bvalid, bready : std_logic := '0';
  signal arvalid, arready, rvalid, rready : std_logic := '0';
  signal bresp, rresp : std_logic_vector(1 downto 0);
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
      intr => intr, irq => irq);

  stimulus : process
    variable failures : natural := 0;
    procedure settle(n : natural := 64) is
    begin
      for i in 1 to n loop wait until falling_edge(clk); end loop;
    end procedure;

    procedure wr(address : natural; value : std_logic_vector(31 downto 0);
                 strobe : natural := 15) is
      variable a_done, w_done : boolean := false;
    begin
      wait until falling_edge(clk);
      awaddr <= std_logic_vector(to_unsigned(address, 9)); wdata <= value;
      wstrb <= std_logic_vector(to_unsigned(strobe, 4)); awvalid <= '1'; wvalid <= '1';
      for cycle in 1 to 512 loop
        wait until rising_edge(clk);
        if awvalid = '1' and awready = '1' then a_done := true; end if;
        if wvalid = '1' and wready = '1' then w_done := true; end if;
        wait until falling_edge(clk);
        if a_done then awvalid <= '0'; end if;
        if w_done then wvalid <= '0'; end if;
        exit when a_done and w_done;
      end loop;
      assert a_done and w_done report "INTC_PROBE: FAIL write request timeout" severity failure;
      bready <= '1';
      for cycle in 1 to 512 loop
        wait until rising_edge(clk);
        exit when bvalid = '1';
      end loop;
      assert bvalid = '1' and not is_x(bresp)
        report "INTC_PROBE: FAIL write response timeout or unknown" severity failure;
      report "INTC_WRITE address=" & integer'image(address) & " strobe=" & integer'image(strobe) &
        " data=" & to_hstring(value) & " response=" & to_hstring(bresp);
      if strobe = 15 then
        assert bresp = "00" report "INTC_PROBE: FAIL full word response" severity failure;
      end if;
      wait until falling_edge(clk); bready <= '0'; settle;
    end procedure;

    procedure rd(address : natural; label_text : string; variable value : out std_logic_vector) is
    begin
      wait until falling_edge(clk);
      araddr <= std_logic_vector(to_unsigned(address, 9)); arvalid <= '1';
      for cycle in 1 to 512 loop
        wait until rising_edge(clk); exit when arready = '1';
      end loop;
      assert arready = '1' report "INTC_PROBE: FAIL read request timeout" severity failure;
      wait until falling_edge(clk); arvalid <= '0'; rready <= '1';
      for cycle in 1 to 512 loop
        wait until rising_edge(clk); exit when rvalid = '1';
      end loop;
      assert rvalid = '1' and rresp = "00" and not is_x(rdata) and (irq = '0' or irq = '1')
        report "INTC_PROBE: FAIL read response" severity failure;
      value := rdata;
      report "INTC_OBSERVATION " & label_text & "=" & to_hstring(rdata) & " irq=" & std_logic'image(irq);
      wait until falling_edge(clk); rready <= '0'; settle;
    end procedure;

    procedure check(address : natural; label_text : string; wanted : std_logic_vector(31 downto 0)) is
      variable value : std_logic_vector(31 downto 0);
    begin
      rd(address, label_text, value);
      if value /= wanted then
        failures := failures+1;
        report "INTC_DIFFERENCE " & label_text & " expected=" & to_hstring(wanted) &
          " actual=" & to_hstring(value) severity warning;
      end if;
    end procedure;

    variable value : std_logic_vector(31 downto 0);
  begin
    settle; resetn <= '1'; settle;
    check(0, "reset_status", x"00000000");
    check(24, "reset_vector", x"FFFFFFFF");
    rd(36, "reset_level", value);
    wr(8, x"FFFFFFFF"); wr(28, x"00000001");
    wr(0, x"FFFFFFFF"); check(0, "software_all", x"0000003F");
    check(4, "pending_all", x"0000003F"); check(24, "priority_zero", x"00000000");
    assert irq = '1' report "INTC_PROBE: FAIL software IRQ" severity failure;
    wr(12, x"00000001"); check(24, "priority_one", x"00000001");
    wr(8, x"00000020"); check(24, "priority_five", x"00000005");
    for i in 0 to 7 loop
      wr(36, std_logic_vector(to_unsigned(i, 32)));
      rd(36, "level_" & integer'image(i), value);
      rd(4, "level_pending_" & integer'image(i), value);
      rd(24, "level_vector_" & integer'image(i), value);
    end loop;
    wr(36, x"FFFFFFFF"); rd(36, "level_unlimited", value);
    wr(12, x"FFFFFFFF"); check(0, "software_clear", x"00000000");
    intr <= "0011"; settle;
    check(0, "hardware_disabled", x"00000000");
    intr <= "1100"; settle;
    wr(28, x"00000003"); wr(28, x"00000000");
    check(28, "hie_write_once", x"00000002");
    rd(0, "status_before_software_write", value);
    wr(28, x"00000001"); wr(8, x"FFFFFFFF");
    wr(0, x"FFFFFFFF"); check(0, "software_after_hie", x"00000030");
    wr(12, x"FFFFFFFF"); intr <= "0011"; settle;
    check(0, "mixed_hardware", x"0000000F");
    intr <= "1100"; settle;
    check(0, "level_retained", x"0000000F");
    wr(12, x"FFFFFFFF"); check(0, "hardware_ack", x"00000000");
    intr <= "0011"; settle; wr(12, x"FFFFFFFF");
    check(0, "ack_while_active", x"0000000A");
    intr <= "1100"; settle; wr(12, x"FFFFFFFF");
    check(0, "released_ack", x"00000000");
    wr(0, x"00000010"); check(0, "software_bit4", x"00000010");
    wr(0, x"00000000"); check(0, "software_zero_preserves", x"00000010");
    wr(0, x"00000020"); check(0, "software_bit5_accumulates", x"00000030");

    -- Partial writes are observations: PG099 does not define their side effects.
    for strobe in 0 to 15 loop
      wr(8, x"00000000"); wr(8, x"FFFFFFFF", strobe);
      rd(8, "strobe_" & integer'image(strobe), value);
    end loop;
    for address in 0 to 9 loop
      rd(address*4, "final_register_" & integer'image(address), value);
    end loop;
    report "INTC_DIFFERENCES count=" & integer'image(failures);
    assert failures = 0 report "INTC_PROBE: FAIL specification differences" severity failure;
    report "INTC_PROBE: COMPLETE";
    finish; wait;
  end process;

  watchdog : process
  begin
    wait for 1 ms;
    assert false report "INTC_PROBE: FAIL watchdog" severity failure;
    wait;
  end process;
end architecture;

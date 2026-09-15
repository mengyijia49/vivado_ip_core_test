library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;

entity tb_master_enable_probe is
end entity;

architecture sim of tb_master_enable_probe is
  signal clk, resetn : std_logic := '0';
  signal irq : std_logic;
  signal intr : std_logic_vector(0 downto 0) := "0";
  signal awaddr, araddr : std_logic_vector(8 downto 0) := (others => '0');
  signal wdata, rdata : std_logic_vector(31 downto 0) := (others => '0');
  signal awvalid, awready, wvalid, wready, bvalid, bready : std_logic := '0';
  signal arvalid, arready, rvalid, rready : std_logic := '0';
  signal bresp, rresp : std_logic_vector(1 downto 0);
begin
  clk <= not clk after 5 ns;
  dut : entity work.probe_0
    port map (
      s_axi_aclk => clk, s_axi_aresetn => resetn,
      s_axi_awaddr => awaddr, s_axi_awvalid => awvalid, s_axi_awready => awready,
      s_axi_wdata => wdata, s_axi_wstrb => "1111", s_axi_wvalid => wvalid, s_axi_wready => wready,
      s_axi_bresp => bresp, s_axi_bvalid => bvalid, s_axi_bready => bready,
      s_axi_araddr => araddr, s_axi_arvalid => arvalid, s_axi_arready => arready,
      s_axi_rdata => rdata, s_axi_rresp => rresp, s_axi_rvalid => rvalid, s_axi_rready => rready,
      intr => intr, irq => irq);

  stimulus : process
    variable differences : natural := 0;
    procedure settle is
    begin
      for i in 1 to 64 loop wait until falling_edge(clk); end loop;
    end procedure;

    procedure wr(address : natural; value : natural) is
      variable a_done, w_done : boolean := false;
    begin
      wait until falling_edge(clk);
      awaddr <= std_logic_vector(to_unsigned(address, 9));
      wdata <= std_logic_vector(to_unsigned(value, 32)); awvalid <= '1'; wvalid <= '1';
      for cycle in 1 to 512 loop
        wait until rising_edge(clk);
        if awvalid = '1' and awready = '1' then a_done := true; end if;
        if wvalid = '1' and wready = '1' then w_done := true; end if;
        wait until falling_edge(clk);
        if a_done then awvalid <= '0'; end if;
        if w_done then wvalid <= '0'; end if;
        exit when a_done and w_done;
      end loop;
      assert a_done and w_done report "MASTER_ENABLE_PROBE: FAIL request timeout" severity failure;
      bready <= '1';
      for cycle in 1 to 512 loop
        wait until rising_edge(clk); exit when bvalid = '1';
      end loop;
      assert bvalid = '1' and bresp = "00"
        report "MASTER_ENABLE_PROBE: FAIL response timeout or error" severity failure;
      report "MASTER_ENABLE address=" & integer'image(address) & " data=" & integer'image(value);
      wait until falling_edge(clk); bready <= '0'; settle;
    end procedure;

    procedure check(address, wanted : natural; label_text : string;
                    expected_irq : std_logic; strict_control : boolean := false) is
      variable mismatch : boolean;
    begin
      wait until falling_edge(clk);
      araddr <= std_logic_vector(to_unsigned(address, 9)); arvalid <= '1';
      for cycle in 1 to 512 loop
        wait until rising_edge(clk); exit when arready = '1';
      end loop;
      assert arready = '1' report "MASTER_ENABLE_PROBE: FAIL read request timeout" severity failure;
      wait until falling_edge(clk); arvalid <= '0'; rready <= '1';
      for cycle in 1 to 512 loop
        wait until rising_edge(clk); exit when rvalid = '1';
      end loop;
      assert rvalid = '1' and rresp = "00" and not is_x(rdata) and (irq = '0' or irq = '1')
        report "MASTER_ENABLE_PROBE: FAIL read response timeout or error" severity failure;
      mismatch := unsigned(rdata) /= wanted or irq /= expected_irq;
      report "MASTER_ENABLE_OBSERVATION " & label_text & " expected=" & integer'image(wanted) &
        " actual=" & to_hstring(rdata) & " irq=" & std_logic'image(irq) &
        " expected_irq=" & std_logic'image(expected_irq);
      if mismatch then
        differences := differences+1;
        report "MASTER_ENABLE_DIFFERENCE " & label_text severity warning;
      end if;
      assert not (mismatch and strict_control)
        report "MASTER_ENABLE_PROBE: FAIL positive control" severity failure;
      wait until falling_edge(clk); rready <= '0'; settle;
    end procedure;

  begin
    resetn <= '0'; settle; resetn <= '1'; settle;
    check(0, 0, "reset", '0', true);
    wr(8, 1); wr(28, 3);
    check(28, 3, "enabled_empty", '0', true);
    intr <= "1"; settle; intr <= "0"; settle;
    check(0, 1, "pending_active", '1', true);
    wr(28, 0);
    check(28, 2, "master_disabled", '0');
    check(0, 1, "pending_retained", '0');
    wr(8, 0);
    check(8, 0, "ier_mask_control", '0', true);
    wr(8, 1);
    check(0, 1, "me_disabled_from_idle", '0', true);
    wr(28, 1);
    check(28, 3, "reenabled", '1', true);
    wr(12, 1);
    check(0, 0, "ack_control", '0', true);
    wr(28, 0);
    intr <= "1"; settle; intr <= "0"; settle;
    check(0, 1, "new_event_while_disabled", '0', true);
    wr(28, 1);
    check(0, 1, "new_event_enabled", '1', true);
    intr <= "0"; resetn <= '0'; settle; resetn <= '1'; settle;
    check(28, 0, "reset_master", '0', true);
    check(0, 0, "reset_pending", '0', true);
    report "MASTER_ENABLE_DIFFERENCES count=" & integer'image(differences);
    assert differences = 0 report "MASTER_ENABLE_PROBE: FAIL ME clear does not mask active IRQ" severity failure;
    report "MASTER_ENABLE_PROBE: PASS";
    finish; wait;
  end process;

  watchdog : process
  begin
    wait for 1 ms;
    assert false report "MASTER_ENABLE_PROBE: FAIL watchdog" severity failure;
    wait;
  end process;
end architecture;

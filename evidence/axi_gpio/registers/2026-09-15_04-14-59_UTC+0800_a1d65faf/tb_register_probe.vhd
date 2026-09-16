library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.env.all;

entity tb_register_probe is
end entity;

architecture sim of tb_register_probe is
  signal clk, resetn : std_logic := '0';
  signal awaddr, araddr : std_logic_vector(8 downto 0) := (others => '0');
  signal wdata, rdata : std_logic_vector(31 downto 0) := (others => '0');
  signal awvalid, awready, wvalid, wready, bvalid, bready : std_logic := '0';
  signal arvalid, arready, rvalid, rready : std_logic := '0';
  signal bresp, rresp : std_logic_vector(1 downto 0);
  signal pins_o, pins_t : std_logic_vector(7 downto 0);
begin
  clk <= not clk after 5 ns;
  dut : entity work.dut_0
    port map (
      s_axi_aclk => clk, s_axi_aresetn => resetn,
      s_axi_awaddr => awaddr, s_axi_awvalid => awvalid, s_axi_awready => awready,
      s_axi_wdata => wdata, s_axi_wstrb => "1111", s_axi_wvalid => wvalid, s_axi_wready => wready,
      s_axi_bresp => bresp, s_axi_bvalid => bvalid, s_axi_bready => bready,
      s_axi_araddr => araddr, s_axi_arvalid => arvalid, s_axi_arready => arready,
      s_axi_rdata => rdata, s_axi_rresp => rresp, s_axi_rvalid => rvalid, s_axi_rready => rready,
      gpio_io_i => x"00", gpio_io_o => pins_o, gpio_io_t => pins_t);

  stimulus : process
    procedure settle is
    begin
      for i in 1 to 64 loop wait until falling_edge(clk); end loop;
    end procedure;

    procedure wr(address : natural; value : std_logic_vector(31 downto 0)) is
      variable a_done, w_done : boolean := false;
    begin
      wait until falling_edge(clk);
      awaddr <= std_logic_vector(to_unsigned(address, 9)); wdata <= value;
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
      assert a_done and w_done report "GPIO_REGISTER_PROBE: FAIL write request timeout" severity failure;
      bready <= '1';
      for cycle in 1 to 512 loop
        wait until rising_edge(clk);
        exit when bvalid = '1';
      end loop;
      assert bvalid = '1' and bresp = "00"
        report "GPIO_REGISTER_PROBE: FAIL write response" severity failure;
      wait until falling_edge(clk); bready <= '0';
      settle;
    end procedure;

    procedure rd(address : natural; label_text : string; variable value : out std_logic_vector(31 downto 0)) is
    begin
      wait until falling_edge(clk);
      araddr <= std_logic_vector(to_unsigned(address, 9)); arvalid <= '1';
      for cycle in 1 to 512 loop
        wait until rising_edge(clk);
        exit when arready = '1';
      end loop;
      assert arready = '1' report "GPIO_REGISTER_PROBE: FAIL read request timeout" severity failure;
      wait until falling_edge(clk); arvalid <= '0'; rready <= '1';
      for cycle in 1 to 512 loop
        wait until rising_edge(clk);
        exit when rvalid = '1';
      end loop;
      assert rvalid = '1' and rresp = "00" and not is_x(rdata)
        report "GPIO_REGISTER_PROBE: FAIL read response" severity failure;
      value := rdata;
      report "GPIO_REGISTER_OBSERVATION " & label_text & "=" & to_hstring(value) &
        " pins=" & to_hstring(pins_o) & " tri=" & to_hstring(pins_t);
      wait until falling_edge(clk); rready <= '0';
      settle;
    end procedure;

    variable value : std_logic_vector(31 downto 0);
  begin
    settle; resetn <= '1'; settle;
    rd(4, "initial_tri", value);
    assert value(7 downto 0) = x"FF" and pins_t = x"FF"
      report "GPIO_REGISTER_PROBE: FAIL reset direction control" severity failure;
    rd(12, "disabled_channel_tri", value);
    wr(4, x"00000000"); wr(0, x"000000A5");
    rd(0, "output_read_control", value);
    assert value(7 downto 0) = x"A5" and pins_o = x"A5" and pins_t = x"00"
      report "GPIO_REGISTER_PROBE: FAIL output write control" severity failure;
    wr(4, x"000000FF"); wr(0, x"0000003C");
    rd(0, "input_read_control", value);
    assert value(7 downto 0) = x"00" and pins_t = x"FF"
      report "GPIO_REGISTER_PROBE: FAIL input read control" severity failure;
    wr(4, x"00000000"); rd(0, "after_input_write", value);
    wr(0, x"000000A5"); rd(16#120#, "disabled_irq_read", value);
    wr(16#120#, x"0000005A"); rd(0, "after_disabled_irq_write", value);
    report "GPIO_REGISTER_PROBE: COMPLETE";
    finish;
    wait;
  end process;

  watchdog : process
  begin
    wait for 1 ms;
    assert false report "GPIO_REGISTER_PROBE: FAIL watchdog" severity failure;
    wait;
  end process;
end architecture;

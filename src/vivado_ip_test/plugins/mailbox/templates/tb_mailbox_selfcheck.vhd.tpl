library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;
use std.env.all;

entity tb_mailbox_selfcheck is end entity;

architecture sim of tb_mailbox_selfcheck is
  constant C_DEPTH : positive := $depth;
  constant C_ERROR_RESPONSE : std_logic_vector(1 downto 0) := $error_response;
  type sl_array is array (0 to 1) of std_logic;
  type slv2_array is array (0 to 1) of std_logic_vector(1 downto 0);
  type slv4_array is array (0 to 1) of std_logic_vector(3 downto 0);
  type slv32_array is array (0 to 1) of std_logic_vector(31 downto 0);
  signal aclk : std_logic := '0';
  signal aresetn : sl_array := (others => '0');
  signal awaddr, wdata, araddr, rdata : slv32_array := (others => (others => '0'));
  signal wstrb : slv4_array := (others => (others => '0'));
  signal bresp, rresp : slv2_array;
  signal awvalid, awready, wvalid, wready, bvalid, bready : sl_array := (others => '0');
  signal arvalid, arready, rvalid, rready : sl_array := (others => '0');
  signal interrupts : sl_array;
begin
  aclk <= not aclk after 5 ns;

  dut : entity work.dut_0 port map (
    S0_AXI_ACLK => aclk, S0_AXI_ARESETN => aresetn(0),
    S0_AXI_AWADDR => awaddr(0), S0_AXI_AWVALID => awvalid(0), S0_AXI_AWREADY => awready(0),
    S0_AXI_WDATA => wdata(0), S0_AXI_WSTRB => wstrb(0), S0_AXI_WVALID => wvalid(0), S0_AXI_WREADY => wready(0),
    S0_AXI_BRESP => bresp(0), S0_AXI_BVALID => bvalid(0), S0_AXI_BREADY => bready(0),
    S0_AXI_ARADDR => araddr(0), S0_AXI_ARVALID => arvalid(0), S0_AXI_ARREADY => arready(0),
    S0_AXI_RDATA => rdata(0), S0_AXI_RRESP => rresp(0), S0_AXI_RVALID => rvalid(0), S0_AXI_RREADY => rready(0),
    S1_AXI_ACLK => aclk, S1_AXI_ARESETN => aresetn(1),
    S1_AXI_AWADDR => awaddr(1), S1_AXI_AWVALID => awvalid(1), S1_AXI_AWREADY => awready(1),
    S1_AXI_WDATA => wdata(1), S1_AXI_WSTRB => wstrb(1), S1_AXI_WVALID => wvalid(1), S1_AXI_WREADY => wready(1),
    S1_AXI_BRESP => bresp(1), S1_AXI_BVALID => bvalid(1), S1_AXI_BREADY => bready(1),
    S1_AXI_ARADDR => araddr(1), S1_AXI_ARVALID => arvalid(1), S1_AXI_ARREADY => arready(1),
    S1_AXI_RDATA => rdata(1), S1_AXI_RRESP => rresp(1), S1_AXI_RVALID => rvalid(1), S1_AXI_RREADY => rready(1),
    Interrupt_0 => interrupts(0), Interrupt_1 => interrupts(1));

  stimulus : process
    file actual_file : text open write_mode is "$actual_path";
    variable row : line;
    variable value : std_logic_vector(31 downto 0);

    procedure record_event(constant event_name : in string) is
    begin write(row, event_name); writeline(actual_file, row); flush(actual_file); end procedure;

    procedure axi_write(constant p, address : in natural;
                        constant data : in std_logic_vector(31 downto 0);
                        constant expected_response : in std_logic_vector(1 downto 0) := "00") is
      variable got_aw, got_w : boolean := false;
      variable cycles : natural := 0;
      variable saved : std_logic_vector(1 downto 0);
    begin
      wait until falling_edge(aclk); awaddr(p) <= std_logic_vector(to_unsigned(address, 32));
      wdata(p) <= data; wstrb(p) <= (others => '1'); awvalid(p) <= '1'; wvalid(p) <= '1';
      while not (got_aw and got_w) loop
        wait until rising_edge(aclk); cycles := cycles+1;
        assert cycles < 256 report "MAILBOX_SELF_CHECK_STATUS: FAIL write request timeout" severity failure;
        if awready(p) = '1' then got_aw := true; end if;
        if wready(p) = '1' then got_w := true; end if;
        wait until falling_edge(aclk);
        if got_aw then awvalid(p) <= '0'; end if; if got_w then wvalid(p) <= '0'; end if;
      end loop;
      cycles := 0;
      loop wait until rising_edge(aclk); cycles := cycles+1;
        assert cycles < 512 report "MAILBOX_SELF_CHECK_STATUS: FAIL write response timeout" severity failure;
        exit when bvalid(p) = '1'; end loop;
      saved := bresp(p);
      for hold in 1 to 2 loop wait until rising_edge(aclk);
        assert bvalid(p) = '1' and bresp(p) = saved
          report "MAILBOX_SELF_CHECK_STATUS: FAIL write response changed under backpressure" severity failure;
      end loop;
      assert saved = expected_response report "MAILBOX_SELF_CHECK_STATUS: FAIL write response" severity failure;
      wait until falling_edge(aclk); bready(p) <= '1'; wait until rising_edge(aclk);
      assert bvalid(p) = '1' report "MAILBOX_SELF_CHECK_STATUS: FAIL write response vanished" severity failure;
      wait until falling_edge(aclk); bready(p) <= '0';
    end procedure;

    procedure axi_read(constant p, address : in natural;
                       variable data : out std_logic_vector(31 downto 0);
                       constant expected_response : in std_logic_vector(1 downto 0) := "00") is
      variable cycles : natural := 0;
      variable saved_data : std_logic_vector(31 downto 0);
      variable saved_response : std_logic_vector(1 downto 0);
    begin
      wait until falling_edge(aclk); araddr(p) <= std_logic_vector(to_unsigned(address, 32)); arvalid(p) <= '1';
      loop wait until rising_edge(aclk); cycles := cycles+1;
        assert cycles < 256 report "MAILBOX_SELF_CHECK_STATUS: FAIL read request timeout" severity failure;
        exit when arready(p) = '1'; end loop;
      wait until falling_edge(aclk); arvalid(p) <= '0'; cycles := 0;
      loop wait until rising_edge(aclk); cycles := cycles+1;
        assert cycles < 512 report "MAILBOX_SELF_CHECK_STATUS: FAIL read response timeout" severity failure;
        exit when rvalid(p) = '1'; end loop;
      saved_data := rdata(p); saved_response := rresp(p);
      for hold in 1 to 2 loop wait until rising_edge(aclk);
        assert rvalid(p) = '1' and rdata(p) = saved_data and rresp(p) = saved_response
          report "MAILBOX_SELF_CHECK_STATUS: FAIL read response changed under backpressure" severity failure;
      end loop;
      assert saved_response = expected_response report "MAILBOX_SELF_CHECK_STATUS: FAIL read response" severity failure;
      data := saved_data; wait until falling_edge(aclk); rready(p) <= '1'; wait until rising_edge(aclk);
      assert rvalid(p) = '1' report "MAILBOX_SELF_CHECK_STATUS: FAIL read response vanished" severity failure;
      wait until falling_edge(aclk); rready(p) <= '0';
    end procedure;

    procedure read_check(constant p, address : in natural;
                         constant expected : in std_logic_vector(31 downto 0)) is
      variable got : std_logic_vector(31 downto 0);
    begin
      axi_read(p, address, got);
      assert got = expected report "MAILBOX_SELF_CHECK_STATUS: FAIL register or FIFO data mismatch" severity failure;
    end procedure;

    procedure settle is
    begin for i in 1 to 6 loop wait until rising_edge(aclk); end loop; end procedure;
  begin
    for i in 1 to 20 loop wait until rising_edge(aclk); end loop;
    wait until falling_edge(aclk); aresetn <= (others => '1'); settle;
    read_check(0, 16#10#, x"00000005"); read_check(1, 16#10#, x"00000005");
    assert interrupts = "00" report "MAILBOX_SELF_CHECK_STATUS: FAIL interrupt after reset" severity failure;
    record_event("RESET_STATUS");

    axi_write(0, 0, x"10203040"); axi_write(0, 0, x"55667788"); axi_write(0, 0, x"DEADBEEF");
    read_check(1, 8, x"10203040"); read_check(1, 8, x"55667788"); read_check(1, 8, x"DEADBEEF");
    read_check(1, 16#10#, x"00000005"); record_event("FIFO_0_TO_1");

    axi_write(1, 0, x"89ABCDEF"); axi_write(1, 0, x"00000001");
    read_check(0, 8, x"89ABCDEF"); read_check(0, 8, x"00000001");
    record_event("FIFO_1_TO_0");

    for i in 0 to C_DEPTH-1 loop axi_write(0, 0, std_logic_vector(to_unsigned(16#1000# + i, 32))); end loop;
    read_check(0, 16#10#, x"00000003"); read_check(1, 16#10#, x"0000000C");
    axi_write(0, 0, x"FFFFFFFF", C_ERROR_RESPONSE);
    read_check(0, 16#14#, x"00000002"); read_check(0, 16#14#, x"00000000");
    record_event("FULL_ERROR");

    for i in 0 to C_DEPTH-1 loop read_check(1, 8, std_logic_vector(to_unsigned(16#1000# + i, 32))); end loop;
    axi_read(1, 8, value, C_ERROR_RESPONSE);
    read_check(1, 16#14#, x"00000001"); read_check(1, 16#14#, x"00000000");
    record_event("EMPTY_ERROR");

    axi_write(0, 0, x"11111111"); axi_write(0, 0, x"22222222");
    axi_write(1, 16#2C#, x"00000002"); settle; read_check(1, 16#10#, x"00000005");
    record_event("CLEAR_RECEIVE");
    axi_write(1, 0, x"33333333"); axi_write(1, 0, x"44444444");
    axi_write(1, 16#2C#, x"00000001"); settle; read_check(0, 16#10#, x"00000005");
    record_event("CLEAR_SEND");

    axi_write(0, 16#20#, x"00000007"); axi_write(0, 16#18#, x"00000002"); axi_write(0, 16#24#, x"00000001");
    axi_write(0, 0, x"00001001"); axi_write(0, 0, x"00001002"); axi_write(0, 0, x"00001003");
    read_check(0, 16#10#, x"00000001"); read_check(1, 8, x"00001001"); settle;
    read_check(0, 16#20#, x"00000001"); read_check(0, 16#28#, x"00000001");
    assert interrupts(0) = '1' report "MAILBOX_SELF_CHECK_STATUS: FAIL send threshold interrupt" severity failure;
    axi_write(0, 16#20#, x"00000001"); axi_write(0, 16#24#, x"00000000"); settle;

    read_check(1, 8, x"00001002"); read_check(1, 8, x"00001003");
    axi_write(1, 16#20#, x"00000007"); axi_write(1, 16#1C#, x"00000001"); axi_write(1, 16#24#, x"00000002");
    axi_write(0, 0, x"00002001"); axi_write(0, 0, x"00002002"); settle;
    read_check(1, 16#20#, x"00000002"); read_check(1, 16#28#, x"00000002");
    assert interrupts(1) = '1' report "MAILBOX_SELF_CHECK_STATUS: FAIL receive threshold interrupt" severity failure;
    axi_write(1, 16#20#, x"00000002"); axi_write(1, 16#24#, x"00000000");
    axi_write(1, 16#2C#, x"00000002"); settle; record_event("THRESHOLD_INTERRUPTS");

    wait until falling_edge(aclk); aresetn <= (others => '0');
    for i in 1 to 20 loop wait until rising_edge(aclk); end loop;
    wait until falling_edge(aclk); aresetn <= (others => '1'); settle;
    read_check(0, 16#10#, x"00000005"); read_check(1, 16#10#, x"00000005");
    read_check(0, 16#24#, x"00000000"); read_check(1, 16#24#, x"00000000");
    assert interrupts = "00" report "MAILBOX_SELF_CHECK_STATUS: FAIL interrupt after runtime reset" severity failure;
    record_event("RESET_RECOVERY");

    report "MAILBOX_SELF_CHECK_STATUS: PASS" severity note; finish; wait;
  end process;

  watchdog : process begin wait for 20 ms;
    assert false report "MAILBOX_SELF_CHECK_STATUS: FAIL watchdog timeout" severity failure; end process;
end architecture;

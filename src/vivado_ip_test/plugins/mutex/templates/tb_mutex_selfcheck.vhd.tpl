library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;
use std.env.all;

entity tb_mutex_selfcheck is
end entity;

architecture sim of tb_mutex_selfcheck is
  constant C_INTERFACES : positive := $interface_count;
  constant C_LAST_INTERFACE : natural := $last_interface;
  constant C_LAST_MUTEX_ADDRESS : natural := $last_mutex_address;
  constant C_MULTIPLE_MUTEXES : boolean := $multiple_mutexes;
  constant C_PROTECTION_VALUE : std_logic_vector(31 downto 0) := x"$protection_value";
  constant C_USER_ENABLED : boolean := $user_enabled;
  type sl_array is array (natural range <>) of std_logic;
  type slv2_array is array (natural range <>) of std_logic_vector(1 downto 0);
  type slv4_array is array (natural range <>) of std_logic_vector(3 downto 0);
  type slv32_array is array (natural range <>) of std_logic_vector(31 downto 0);
  signal aclk : std_logic := '0';
  signal aresetn : sl_array(0 to C_INTERFACES-1) := (others => '0');
  signal awaddr, wdata, araddr, rdata : slv32_array(0 to C_INTERFACES-1) := (others => (others => '0'));
  signal wstrb : slv4_array(0 to C_INTERFACES-1) := (others => (others => '0'));
  signal bresp, rresp : slv2_array(0 to C_INTERFACES-1);
  signal awvalid, awready, wvalid, wready, bvalid, bready : sl_array(0 to C_INTERFACES-1) := (others => '0');
  signal arvalid, arready, rvalid, rready : sl_array(0 to C_INTERFACES-1) := (others => '0');
begin
  aclk <= not aclk after 5 ns;

  dut : entity work.dut_0
    port map (
$port_map
    );

  stimulus : process
    file actual_file : text open write_mode is "$actual_path";
    variable output_line : line;
    variable seen : boolean_vector(0 to C_INTERFACES-1);
    variable cycles : natural;

    procedure record_event(constant value : in string) is
    begin
      write(output_line, value); writeline(actual_file, output_line); flush(actual_file);
    end procedure;

    procedure axi_write(constant port_index : in natural;
                        constant address : in natural;
                        constant value : in std_logic_vector(31 downto 0)) is
      variable got_address, got_data : boolean;
      variable saved_response : std_logic_vector(1 downto 0);
      variable wait_cycles : natural;
    begin
      wait until falling_edge(aclk);
      awaddr(port_index) <= std_logic_vector(to_unsigned(address, 32));
      wdata(port_index) <= value; wstrb(port_index) <= (others => '1');
      awvalid(port_index) <= '1'; wvalid(port_index) <= '1'; bready(port_index) <= '0';
      got_address := false; got_data := false; wait_cycles := 0;
      while not (got_address and got_data) loop
        wait until rising_edge(aclk); wait_cycles := wait_cycles + 1;
        assert wait_cycles < 256 report "MUTEX_SELF_CHECK_STATUS: FAIL write request timeout" severity failure;
        if awready(port_index) = '1' then got_address := true; end if;
        if wready(port_index) = '1' then got_data := true; end if;
        wait until falling_edge(aclk);
        if got_address then awvalid(port_index) <= '0'; end if;
        if got_data then wvalid(port_index) <= '0'; end if;
      end loop;
      wait_cycles := 0;
      loop
        wait until rising_edge(aclk); wait_cycles := wait_cycles + 1;
        assert wait_cycles < 512 report "MUTEX_SELF_CHECK_STATUS: FAIL write response timeout" severity failure;
        exit when bvalid(port_index) = '1';
      end loop;
      saved_response := bresp(port_index);
      for hold in 1 to 2 loop
        wait until rising_edge(aclk);
        assert bvalid(port_index) = '1' and bresp(port_index) = saved_response
          report "MUTEX_SELF_CHECK_STATUS: FAIL write response changed under backpressure" severity failure;
      end loop;
      assert saved_response = "00" report "MUTEX_SELF_CHECK_STATUS: FAIL write response" severity failure;
      wait until falling_edge(aclk); bready(port_index) <= '1';
      wait until rising_edge(aclk);
      assert bvalid(port_index) = '1' report "MUTEX_SELF_CHECK_STATUS: FAIL write response vanished" severity failure;
      wait until falling_edge(aclk); bready(port_index) <= '0';
    end procedure;

    procedure axi_read_check(constant port_index : in natural;
                             constant address : in natural;
                             constant expected : in std_logic_vector(31 downto 0)) is
      variable saved_data : std_logic_vector(31 downto 0);
      variable saved_response : std_logic_vector(1 downto 0);
      variable wait_cycles : natural;
    begin
      wait until falling_edge(aclk);
      araddr(port_index) <= std_logic_vector(to_unsigned(address, 32));
      arvalid(port_index) <= '1'; rready(port_index) <= '0'; wait_cycles := 0;
      loop
        wait until rising_edge(aclk); wait_cycles := wait_cycles + 1;
        assert wait_cycles < 256 report "MUTEX_SELF_CHECK_STATUS: FAIL read request timeout" severity failure;
        exit when arready(port_index) = '1';
      end loop;
      wait until falling_edge(aclk); arvalid(port_index) <= '0'; wait_cycles := 0;
      loop
        wait until rising_edge(aclk); wait_cycles := wait_cycles + 1;
        assert wait_cycles < 512 report "MUTEX_SELF_CHECK_STATUS: FAIL read response timeout" severity failure;
        exit when rvalid(port_index) = '1';
      end loop;
      saved_data := rdata(port_index); saved_response := rresp(port_index);
      for hold in 1 to 2 loop
        wait until rising_edge(aclk);
        assert rvalid(port_index) = '1' and rdata(port_index) = saved_data and rresp(port_index) = saved_response
          report "MUTEX_SELF_CHECK_STATUS: FAIL read response changed under backpressure" severity failure;
      end loop;
      assert saved_response = "00" report "MUTEX_SELF_CHECK_STATUS: FAIL read response" severity failure;
      assert saved_data = expected report "MUTEX_SELF_CHECK_STATUS: FAIL register mismatch" severity failure;
      wait until falling_edge(aclk); rready(port_index) <= '1';
      wait until rising_edge(aclk);
      assert rvalid(port_index) = '1' report "MUTEX_SELF_CHECK_STATUS: FAIL read response vanished" severity failure;
      wait until falling_edge(aclk); rready(port_index) <= '0';
    end procedure;

    procedure check_initial_port(constant port_index : in natural) is
    begin
      axi_read_check(port_index, 0, x"00000000");
    end procedure;

    procedure check_owner_port(constant port_index : in natural) is
    begin
      axi_read_check(port_index, 0, x"00000025");
    end procedure;
  begin
    for cycle in 1 to 12 loop wait until rising_edge(aclk); end loop;
    wait until falling_edge(aclk); aresetn <= (others => '1');
$initial_setup
$reset_read_calls
    record_event("RESET_READY");

    axi_write(0, 0, x"00000025");
    axi_read_check(0, 0, x"00000025"); record_event("PORT0_ACQUIRE");
$visible_read_calls
    record_event("CROSS_PORT_VISIBLE");

    axi_write(1, 0, x"00000069");
    axi_read_check(0, 0, x"00000025"); record_event("FOREIGN_OWNER_BLOCKED");

    axi_write(1, 0, x"00000024");
    axi_read_check(0, 0, C_PROTECTION_VALUE);
    if C_PROTECTION_VALUE /= x"00000000" then axi_write(0, 0, x"00000024"); end if;
    axi_read_check(0, 0, x"00000000"); record_event("PROTECTION_RULE");

    if C_USER_ENABLED then
      axi_write(C_LAST_INTERFACE, 4, x"A55A3CC3");
      axi_read_check(0, 4, x"A55A3CC3");
    else
      axi_read_check(0, 4, x"00000000");
    end if;
    record_event("USER_SHARED");

    axi_write(C_LAST_INTERFACE, C_LAST_MUTEX_ADDRESS, x"000000AD");
    axi_read_check(0, C_LAST_MUTEX_ADDRESS, x"000000AD");
    if C_MULTIPLE_MUTEXES then axi_read_check(0, 0, x"00000000"); end if;
    axi_write(C_LAST_INTERFACE, C_LAST_MUTEX_ADDRESS, x"000000AC");
    record_event("LAST_MUTEX");

    wait until falling_edge(aclk);
$competition_drives
    seen := (others => false); cycles := 0;
    loop
      wait until rising_edge(aclk); cycles := cycles + 1;
      assert cycles < 256 report "MUTEX_SELF_CHECK_STATUS: FAIL simultaneous request timeout" severity failure;
      for i in 0 to C_INTERFACES-1 loop
        if awready(i) = '1' then awvalid(i) <= '0'; end if;
        if wready(i) = '1' then wvalid(i) <= '0'; end if;
        if bvalid(i) = '1' then
          assert bresp(i) = "00" report "MUTEX_SELF_CHECK_STATUS: FAIL simultaneous response" severity failure;
          seen(i) := true;
        end if;
      end loop;
      exit when seen = (seen'range => true);
    end loop;
    wait until falling_edge(aclk); bready <= (others => '0');
    axi_read_check(C_LAST_INTERFACE, 0, x"00000003");
    axi_write(0, 0, x"00000002"); record_event("SIMULTANEOUS_PRIORITY");

    axi_write(0, 0, x"000000EF");
    wait until falling_edge(aclk); aresetn <= (others => '0');
    for cycle in 1 to 12 loop wait until rising_edge(aclk); end loop;
    wait until falling_edge(aclk); aresetn <= (others => '1');
    if C_MULTIPLE_MUTEXES then
      axi_write(0, 0, x"000000EE");
      axi_write(0, C_LAST_MUTEX_ADDRESS, x"00000000");
      if C_USER_ENABLED then axi_write(0, 4, x"00000000"); end if;
    end if;
    axi_read_check(0, 0, x"00000000");
    axi_read_check(0, C_LAST_MUTEX_ADDRESS, x"00000000");
    axi_read_check(0, 4, x"00000000"); record_event("RESET_CLEARS");

    report "MUTEX_SELF_CHECK_STATUS: PASS" severity note;
    finish;
    wait;
  end process;

  watchdog : process
  begin
    wait for 2 ms;
    assert false report "MUTEX_SELF_CHECK_STATUS: FAIL watchdog timeout" severity failure;
  end process;
end architecture;

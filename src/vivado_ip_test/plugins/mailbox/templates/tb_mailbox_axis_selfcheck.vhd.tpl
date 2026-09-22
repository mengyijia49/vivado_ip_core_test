library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;
use std.env.all;

entity tb_mailbox_axis_selfcheck is end entity;

architecture sim of tb_mailbox_axis_selfcheck is
  constant C_DEPTH : positive := $depth;
  constant C_VECTOR_COUNT : positive := $vector_count;
  constant C_CONCURRENT_COUNT : positive := 12;
  type sl_array is array (0 to 1) of std_logic;
  type slv32_array is array (0 to 1) of std_logic_vector(31 downto 0);
  type data_vectors is array (natural range <>) of std_logic_vector(31 downto 0);
  type last_vectors is array (natural range <>) of std_logic;
  constant C_S0_DATA : data_vectors(0 to C_VECTOR_COUNT-1) := ($s0_data);
  constant C_S0_LAST : last_vectors(0 to C_VECTOR_COUNT-1) := ($s0_last);
  constant C_S1_DATA : data_vectors(0 to C_VECTOR_COUNT-1) := ($s1_data);
  constant C_S1_LAST : last_vectors(0 to C_VECTOR_COUNT-1) := ($s1_last);
  constant C_M0_DATA : data_vectors(0 to C_VECTOR_COUNT-1) := ($m0_data);
  constant C_M0_LAST : last_vectors(0 to C_VECTOR_COUNT-1) := ($m0_last);
  constant C_M1_DATA : data_vectors(0 to C_VECTOR_COUNT-1) := ($m1_data);
  constant C_M1_LAST : last_vectors(0 to C_VECTOR_COUNT-1) := ($m1_last);
  signal aclk : std_logic := '0';
  signal sys_rst : std_logic := '1';
  signal s_tdata : slv32_array := (others => (others => '0'));
  signal s_tlast, s_tvalid, s_tready : sl_array := (others => '0');
  signal m_tdata : slv32_array;
  signal m_tlast, m_tvalid : sl_array;
  signal m_tready : sl_array := (others => '0');
  signal interrupts : sl_array;
begin
  aclk <= not aclk after 5 ns;

  dut : entity work.dut_0 port map (
    SYS_Rst => sys_rst,
    S0_AXIS_ACLK => aclk, S0_AXIS_TDATA => s_tdata(0), S0_AXIS_TLAST => s_tlast(0),
    S0_AXIS_TVALID => s_tvalid(0), S0_AXIS_TREADY => s_tready(0),
    M0_AXIS_ACLK => aclk, M0_AXIS_TDATA => m_tdata(0), M0_AXIS_TLAST => m_tlast(0),
    M0_AXIS_TVALID => m_tvalid(0), M0_AXIS_TREADY => m_tready(0),
    S1_AXIS_ACLK => aclk, S1_AXIS_TDATA => s_tdata(1), S1_AXIS_TLAST => s_tlast(1),
    S1_AXIS_TVALID => s_tvalid(1), S1_AXIS_TREADY => s_tready(1),
    M1_AXIS_ACLK => aclk, M1_AXIS_TDATA => m_tdata(1), M1_AXIS_TLAST => m_tlast(1),
    M1_AXIS_TVALID => m_tvalid(1), M1_AXIS_TREADY => m_tready(1),
    Interrupt_0 => interrupts(0), Interrupt_1 => interrupts(1));

  stimulus : process
    file actual_file : text open write_mode is "$actual_path";
    variable row : line;
    variable sent0, sent1, got0, got1, cycles : natural;
    variable hold0, hold1 : boolean;
    variable held_data0, held_data1 : std_logic_vector(31 downto 0);
    variable held_last0, held_last1 : std_logic;
    variable tlast_failed : boolean := false;

    procedure record_event(constant event_name : in string) is
    begin write(row, event_name); writeline(actual_file, row); flush(actual_file); end procedure;

    procedure send_beat(signal data : out std_logic_vector(31 downto 0);
                        signal last, valid : out std_logic; signal ready : in std_logic;
                        constant value : in std_logic_vector(31 downto 0);
                        constant is_last : in std_logic) is
      variable waited : natural := 0;
    begin
      wait until falling_edge(aclk); data <= value; last <= is_last; valid <= '1';
      loop
        wait until rising_edge(aclk); waited := waited + 1;
        assert waited < 1024 report "MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL input timeout" severity failure;
        exit when ready = '1';
      end loop;
      wait until falling_edge(aclk); valid <= '0'; last <= '0';
    end procedure;

    procedure receive_beat(signal data : in std_logic_vector(31 downto 0);
                           signal last, valid : in std_logic; signal ready : out std_logic;
                           constant expected_data : in std_logic_vector(31 downto 0);
                           constant expected_last : in std_logic) is
      variable waited : natural := 0;
      variable saved_data : std_logic_vector(31 downto 0);
      variable saved_last : std_logic;
    begin
      ready <= '0';
      loop
        wait until rising_edge(aclk); waited := waited + 1;
        assert waited < 2048 report "MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL output timeout" severity failure;
        exit when valid = '1';
      end loop;
      saved_data := data; saved_last := last;
      for i in 1 to 3 loop
        wait until rising_edge(aclk);
        assert valid = '1' and data = saved_data and last = saved_last
          report "MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL output changed under backpressure" severity failure;
      end loop;
      assert saved_data = expected_data
        report "MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL output data mismatch actual=" &
               to_hstring(saved_data) & " expected=" & to_hstring(expected_data)
        severity failure;
      if saved_last /= expected_last then
        report "MAILBOX_AXIS_TLAST_MISMATCH actual=" & std_logic'image(saved_last) &
               " expected=" & std_logic'image(expected_last) severity error;
        tlast_failed := true;
      end if;
      wait until falling_edge(aclk); ready <= '1';
      wait until rising_edge(aclk);
      assert valid = '1' report "MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL output vanished before handshake" severity failure;
      wait until falling_edge(aclk); ready <= '0';
    end procedure;
  begin
    for i in 1 to 20 loop wait until rising_edge(aclk); end loop;
    wait until falling_edge(aclk); sys_rst <= '0';
    for i in 1 to 10 loop wait until rising_edge(aclk); end loop;
    assert m_tvalid = "00" report "MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL output valid after reset" severity failure;
    record_event("RESET");

    for i in 0 to C_VECTOR_COUNT-1 loop
      send_beat(s_tdata(0), s_tlast(0), s_tvalid(0), s_tready(0), C_S0_DATA(i), C_S0_LAST(i));
    end loop;
    for i in 0 to C_VECTOR_COUNT-1 loop
      receive_beat(m_tdata(1), m_tlast(1), m_tvalid(1), m_tready(1), C_M1_DATA(i), C_M1_LAST(i));
    end loop;
    record_event("S0_TO_M1");

    for i in 0 to C_VECTOR_COUNT-1 loop
      send_beat(s_tdata(1), s_tlast(1), s_tvalid(1), s_tready(1), C_S1_DATA(i), C_S1_LAST(i));
    end loop;
    for i in 0 to C_VECTOR_COUNT-1 loop
      receive_beat(m_tdata(0), m_tlast(0), m_tvalid(0), m_tready(0), C_M0_DATA(i), C_M0_LAST(i));
    end loop;
    record_event("S1_TO_M0");

    m_tready(1) <= '0';
    for i in 0 to C_DEPTH-1 loop
      send_beat(s_tdata(0), s_tlast(0), s_tvalid(0), s_tready(0),
                std_logic_vector(to_unsigned(16#1000# + i, 32)),
                '1' when i = C_DEPTH-1 else '0');
    end loop;
    wait until falling_edge(aclk); s_tdata(0) <= x"BAD0BAD0"; s_tlast(0) <= '1'; s_tvalid(0) <= '1';
    for i in 1 to 5 loop
      wait until rising_edge(aclk);
      assert s_tready(0) = '0' report "MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL full FIFO accepted extra data" severity failure;
    end loop;
    wait until falling_edge(aclk); s_tvalid(0) <= '0'; s_tlast(0) <= '0';
    for i in 0 to C_DEPTH-1 loop
      receive_beat(m_tdata(1), m_tlast(1), m_tvalid(1), m_tready(1),
                   std_logic_vector(to_unsigned(16#1000# + i, 32)),
                   '1' when i = C_DEPTH-1 else '0');
    end loop;
    record_event("FIFO_FULL_BACKPRESSURE");

    sent0 := 0; sent1 := 0; got0 := 0; got1 := 0; cycles := 0;
    hold0 := false; hold1 := false;
    while got0 < C_CONCURRENT_COUNT or got1 < C_CONCURRENT_COUNT loop
      wait until falling_edge(aclk);
      if sent0 < C_CONCURRENT_COUNT then
        s_tvalid(0) <= '1'; s_tdata(0) <= std_logic_vector(to_unsigned(16#60000000# + sent0, 32));
        if sent0 mod 4 = 3 then s_tlast(0) <= '1'; else s_tlast(0) <= '0'; end if;
      else s_tvalid(0) <= '0'; s_tlast(0) <= '0'; end if;
      if sent1 < C_CONCURRENT_COUNT then
        s_tvalid(1) <= '1'; s_tdata(1) <= std_logic_vector(to_unsigned(16#70000000# + sent1, 32));
        if sent1 mod 3 = 2 then s_tlast(1) <= '1'; else s_tlast(1) <= '0'; end if;
      else s_tvalid(1) <= '0'; s_tlast(1) <= '0'; end if;
      if cycles mod 5 = 1 or cycles mod 5 = 2 then m_tready(0) <= '0'; else m_tready(0) <= '1'; end if;
      if cycles mod 7 = 3 or cycles mod 7 = 4 or cycles mod 7 = 5 then m_tready(1) <= '0'; else m_tready(1) <= '1'; end if;
      wait until rising_edge(aclk); cycles := cycles + 1;
      assert cycles < 2048 report "MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL concurrent transfer timeout" severity failure;
      if hold0 then
        assert m_tvalid(0) = '1' and m_tdata(0) = held_data0 and m_tlast(0) = held_last0
          report "MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL M0 changed while stalled" severity failure;
      end if;
      if hold1 then
        assert m_tvalid(1) = '1' and m_tdata(1) = held_data1 and m_tlast(1) = held_last1
          report "MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL M1 changed while stalled" severity failure;
      end if;
      if m_tvalid(0) = '1' and m_tready(0) = '1' then
        assert m_tdata(0) = std_logic_vector(to_unsigned(16#70000000# + got0, 32))
          report "MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL M0 order or routing" severity failure;
        if (got0 mod 3 = 2 and m_tlast(0) /= '1') or
           (got0 mod 3 /= 2 and m_tlast(0) /= '0') then
          report "MAILBOX_AXIS_TLAST_MISMATCH on M0 concurrent transfer" severity error;
          tlast_failed := true;
        end if;
        got0 := got0 + 1;
      end if;
      if m_tvalid(1) = '1' and m_tready(1) = '1' then
        assert m_tdata(1) = std_logic_vector(to_unsigned(16#60000000# + got1, 32))
          report "MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL M1 order or routing" severity failure;
        if (got1 mod 4 = 3 and m_tlast(1) /= '1') or
           (got1 mod 4 /= 3 and m_tlast(1) /= '0') then
          report "MAILBOX_AXIS_TLAST_MISMATCH on M1 concurrent transfer" severity error;
          tlast_failed := true;
        end if;
        got1 := got1 + 1;
      end if;
      if s_tvalid(0) = '1' and s_tready(0) = '1' then sent0 := sent0 + 1; end if;
      if s_tvalid(1) = '1' and s_tready(1) = '1' then sent1 := sent1 + 1; end if;
      hold0 := m_tvalid(0) = '1' and m_tready(0) = '0';
      hold1 := m_tvalid(1) = '1' and m_tready(1) = '0';
      held_data0 := m_tdata(0); held_last0 := m_tlast(0);
      held_data1 := m_tdata(1); held_last1 := m_tlast(1);
    end loop;
    wait until falling_edge(aclk); s_tvalid <= "00"; m_tready <= "00";
    record_event("BIDIRECTIONAL_CONCURRENT");

    send_beat(s_tdata(0), s_tlast(0), s_tvalid(0), s_tready(0), x"11111111", '0');
    send_beat(s_tdata(1), s_tlast(1), s_tvalid(1), s_tready(1), x"22222222", '1');
    wait until falling_edge(aclk); sys_rst <= '1';
    for i in 1 to 20 loop wait until rising_edge(aclk); end loop;
    wait until falling_edge(aclk); sys_rst <= '0';
    for i in 1 to 10 loop wait until rising_edge(aclk); end loop;
    assert m_tvalid = "00" report "MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL reset did not flush data" severity failure;
    record_event("RESET_FLUSH");

    if tlast_failed then
      report "MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL TLAST was not preserved" severity note;
    else
      report "MAILBOX_AXIS_SELF_CHECK_STATUS: PASS" severity note;
    end if;
    finish; wait;
  end process;

  watchdog : process begin wait for 20 ms;
    assert false report "MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL watchdog timeout" severity failure; end process;
end architecture;

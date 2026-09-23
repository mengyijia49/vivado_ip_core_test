library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;

entity tb_axi_lmb_selfcheck is
end entity;

architecture test of tb_axi_lmb_selfcheck is
  constant DATA_WIDTH : positive := 32;
  constant ADDR_WIDTH : positive := 32;
  constant ID_WIDTH : positive := 1;
  constant LANES : positive := 4;
  constant ACCESS_COUNT : natural := 6;
  constant OPERATION_COUNT : natural := 5;
  constant FREQUENCY_PROTOCOL : boolean := 1 = 1;
  type natural_array is array(natural range <>) of natural;
  type address_array is array(natural range <>) of std_logic_vector(31 downto 0);
  type data_array is array(natural range <>) of std_logic_vector(31 downto 0);
  type be_array is array(natural range <>) of std_logic_vector(3 downto 0);
  type protection_array is array(natural range <>) of std_logic_vector(1 downto 0);
  constant EXPECTED_ADDR : address_array(0 to 5) := (0 => "00000000000000000000000011110000", 1 => "00000000000000000000000011110100", 2 => "00000000000000000000001011000000", 3 => "00000000000000000000001011010000", 4 => "00000000000000000000001011100000", 5 => "00000000000000000000001011110000");
  constant EXPECTED_READ : natural_array(0 to 5) := (1, 1, 1, 0, 0, 1);
  constant EXPECTED_WRITE : natural_array(0 to 5) := (0, 0, 0, 1, 1, 0);
  constant EXPECTED_DATA : data_array(0 to 5) := (0 => "00000000000000000000000000000000", 1 => "00000000000000000000000000000000", 2 => "00000000000000000000000000000000", 3 => "00010010001101000101011001111000", 4 => "10000111011001010100001100100001", 5 => "00000000000000000000000000000000");
  constant EXPECTED_BE : be_array(0 to 5) := (0 => "0000", 1 => "0000", 2 => "0000", 3 => "1111", 4 => "1111", 5 => "0000");
  constant EXPECTED_PROT : protection_array(0 to 5) := (0 => "01", 1 => "01", 2 => "01", 3 => "01", 4 => "01", 5 => "01");

  signal Clk : std_logic := '0';
  signal Rst : std_logic := '1';

  signal S_AXI_AWID : std_logic_vector(ID_WIDTH-1 downto 0) := (others => '0');
  signal S_AXI_AWADDR : std_logic_vector(ADDR_WIDTH-1 downto 0) := (others => '0');
  signal S_AXI_AWLEN : std_logic_vector(7 downto 0) := (others => '0');
  signal S_AXI_AWSIZE : std_logic_vector(2 downto 0) := (others => '0');
  signal S_AXI_AWBURST : std_logic_vector(1 downto 0) := (others => '0');
  signal S_AXI_AWVALID : std_logic := '0';
  signal S_AXI_AWPROT : std_logic_vector(2 downto 0) := (others => '0');
  signal S_AXI_AWREADY : std_logic;
  signal S_AXI_WDATA : std_logic_vector(DATA_WIDTH-1 downto 0) := (others => '0');
  signal S_AXI_WSTRB : std_logic_vector(LANES-1 downto 0) := (others => '0');
  signal S_AXI_WLAST, S_AXI_WVALID, S_AXI_WREADY : std_logic := '0';
  signal S_AXI_BID : std_logic_vector(ID_WIDTH-1 downto 0);
  signal S_AXI_BRESP : std_logic_vector(1 downto 0);
  signal S_AXI_BVALID : std_logic;
  signal S_AXI_BREADY : std_logic := '0';
  signal S_AXI_ARID : std_logic_vector(ID_WIDTH-1 downto 0) := (others => '0');
  signal S_AXI_ARADDR : std_logic_vector(ADDR_WIDTH-1 downto 0) := (others => '0');
  signal S_AXI_ARLEN : std_logic_vector(7 downto 0) := (others => '0');
  signal S_AXI_ARSIZE : std_logic_vector(2 downto 0) := (others => '0');
  signal S_AXI_ARBURST : std_logic_vector(1 downto 0) := (others => '0');
  signal S_AXI_ARVALID : std_logic := '0';
  signal S_AXI_ARPROT : std_logic_vector(2 downto 0) := (others => '0');
  signal S_AXI_ARREADY : std_logic;
  signal S_AXI_RID : std_logic_vector(ID_WIDTH-1 downto 0);
  signal S_AXI_RDATA : std_logic_vector(DATA_WIDTH-1 downto 0);
  signal S_AXI_RRESP : std_logic_vector(1 downto 0);
  signal S_AXI_RLAST, S_AXI_RVALID : std_logic;
  signal S_AXI_RREADY : std_logic := '0';
  signal M_ABus : std_logic_vector(ADDR_WIDTH-1 downto 0);
  signal M_Prot : std_logic_vector(1 downto 0);
  signal M_ReadStrobe, M_WriteStrobe, M_AddrStrobe : std_logic;
  signal M_DBus : std_logic_vector(DATA_WIDTH-1 downto 0);
  signal M_BE : std_logic_vector(LANES-1 downto 0);
  signal LMB_ReadDBus : std_logic_vector(DATA_WIDTH-1 downto 0) := (others => '0');
  signal LMB_Ready, LMB_UE : std_logic := '0';
  signal LMB_Wait : std_logic := '1';
  signal LMB_CE : std_logic := '0';
  signal read_data_now, read_data_delayed : std_logic_vector(DATA_WIDTH-1 downto 0) := (others => '0');
  signal read_ue_now, read_ue_delayed, write_ue_now : std_logic := '0';
  signal request_is_read : std_logic := '0';
  signal fault_mode : natural range 0 to 2 := 0;
  signal wait_limit : natural range 0 to 3 := 0;
  signal wait_count : natural range 0 to 3 := 0;
  signal access_index : natural range 0 to ACCESS_COUNT := 0;
  signal aw_handshakes, w_handshakes, wlast_handshakes : natural := 0;
  type responder_state_t is (IDLE, WAITING, COMPLETE_GAP);
  signal responder_state : responder_state_t := IDLE;

  function read_value(address : std_logic_vector) return std_logic_vector is
    variable result : std_logic_vector(DATA_WIDTH-1 downto 0) := (others => '0');
    variable base : natural;
  begin
    base := to_integer(unsigned(address(15 downto 0)));
    for lane in 0 to LANES-1 loop
      result(lane*8+7 downto lane*8) := std_logic_vector(to_unsigned((base + lane*49) mod 256, 8));
    end loop;
    return result;
  end function;

  function beat_value(base : std_logic_vector; beat : natural) return std_logic_vector is
    variable result : unsigned(DATA_WIDTH-1 downto 0) := unsigned(base);
  begin
    result := result xor resize(to_unsigned(beat*257, 32), DATA_WIDTH);
    return std_logic_vector(result);
  end function;

  procedure write_bit(variable target : inout line; value : std_logic) is
  begin
    if value = '1' then
      write(target, character'('1'));
    else
      write(target, character'('0'));
    end if;
  end procedure;

  procedure write_bits(variable target : inout line; value : std_logic_vector) is
  begin
    for index in value'range loop
      write_bit(target, value(index));
    end loop;
  end procedure;
begin
  Clk <= not Clk after 5 ns;

  -- Frequency reads return data and UE one cycle after Ready; writes do not.
  LMB_ReadDBus <= read_data_delayed when FREQUENCY_PROTOCOL else read_data_now;
  LMB_UE <= (read_ue_delayed or write_ue_now) when FREQUENCY_PROTOCOL else
            (read_ue_now or write_ue_now);

  dut : entity work.dut_0
    port map (
      Clk => Clk, Rst => Rst,
      S_AXI_AWID => S_AXI_AWID, S_AXI_AWADDR => S_AXI_AWADDR,
      S_AXI_AWLEN => S_AXI_AWLEN, S_AXI_AWSIZE => S_AXI_AWSIZE,
      S_AXI_AWBURST => S_AXI_AWBURST, S_AXI_AWVALID => S_AXI_AWVALID,
      S_AXI_AWPROT => S_AXI_AWPROT, S_AXI_AWREADY => S_AXI_AWREADY,
      S_AXI_WDATA => S_AXI_WDATA, S_AXI_WSTRB => S_AXI_WSTRB,
      S_AXI_WLAST => S_AXI_WLAST, S_AXI_WVALID => S_AXI_WVALID,
      S_AXI_WREADY => S_AXI_WREADY, S_AXI_BID => S_AXI_BID,
      S_AXI_BRESP => S_AXI_BRESP, S_AXI_BVALID => S_AXI_BVALID,
      S_AXI_BREADY => S_AXI_BREADY, S_AXI_ARID => S_AXI_ARID,
      S_AXI_ARADDR => S_AXI_ARADDR, S_AXI_ARLEN => S_AXI_ARLEN,
      S_AXI_ARSIZE => S_AXI_ARSIZE, S_AXI_ARBURST => S_AXI_ARBURST,
      S_AXI_ARVALID => S_AXI_ARVALID, S_AXI_ARPROT => S_AXI_ARPROT,
      S_AXI_ARREADY => S_AXI_ARREADY, S_AXI_RID => S_AXI_RID,
      S_AXI_RDATA => S_AXI_RDATA, S_AXI_RRESP => S_AXI_RRESP,
      S_AXI_RLAST => S_AXI_RLAST, S_AXI_RVALID => S_AXI_RVALID,
      S_AXI_RREADY => S_AXI_RREADY, M_ABus => M_ABus,
      M_ReadStrobe => M_ReadStrobe, M_WriteStrobe => M_WriteStrobe,
      M_AddrStrobe => M_AddrStrobe, M_DBus => M_DBus, M_BE => M_BE,
      LMB_ReadDBus => LMB_ReadDBus, LMB_Ready => LMB_Ready,
      LMB_Wait => LMB_Wait, LMB_UE => LMB_UE, LMB_CE => LMB_CE,
      M_Prot => M_Prot
    );

  lmb_responder : process(Clk)
  begin
    if rising_edge(Clk) then
      LMB_Ready <= '0';
      read_ue_now <= '0';
      write_ue_now <= '0';
      read_data_delayed <= read_data_now;
      read_ue_delayed <= read_ue_now;
      LMB_Wait <= '1';
      if Rst = '1' then
        wait_count <= 0;
        responder_state <= IDLE;
        access_index <= 0;
        read_data_now <= (others => '0');
        read_data_delayed <= (others => '0');
        read_ue_delayed <= '0';
        request_is_read <= '0';
      else
        case responder_state is
          when IDLE =>
            if M_AddrStrobe = '1' then
              assert access_index < ACCESS_COUNT
                report "AXI_LMB_SELF_CHECK_STATUS: FAIL extra LMB access" severity failure;
              assert M_ABus = EXPECTED_ADDR(access_index)
                report "AXI_LMB_SELF_CHECK_STATUS: FAIL LMB address mismatch" severity failure;
              assert M_ReadStrobe = std_logic'val(EXPECTED_READ(access_index)+2) and
                     M_WriteStrobe = std_logic'val(EXPECTED_WRITE(access_index)+2)
                report "AXI_LMB_SELF_CHECK_STATUS: FAIL LMB direction mismatch index=" &
                  integer'image(access_index) & " read=" & std_logic'image(M_ReadStrobe) &
                  " write=" & std_logic'image(M_WriteStrobe) & " expected_read=" &
                  integer'image(EXPECTED_READ(access_index)) & " expected_write=" &
                  integer'image(EXPECTED_WRITE(access_index)) severity failure;
              assert M_DBus = EXPECTED_DATA(access_index) and M_BE = EXPECTED_BE(access_index)
                report "AXI_LMB_SELF_CHECK_STATUS: FAIL LMB write payload mismatch" severity failure;
              access_index <= access_index + 1;
              read_data_now <= read_value(M_ABus);
              request_is_read <= M_ReadStrobe;
              wait_count <= 0;
              responder_state <= WAITING;
            end if;
          when WAITING =>
            if fault_mode = 1 then
              LMB_Wait <= '0';
              responder_state <= COMPLETE_GAP;
            elsif wait_count < wait_limit then
              wait_count <= wait_count + 1;
            else
              LMB_Ready <= '1';
              if fault_mode = 2 then
                read_ue_now <= request_is_read;
                write_ue_now <= not request_is_read;
              end if;
              responder_state <= COMPLETE_GAP;
            end if;
          when COMPLETE_GAP =>
            wait_count <= 0;
            if M_AddrStrobe = '1' then
              assert access_index < ACCESS_COUNT
                report "AXI_LMB_SELF_CHECK_STATUS: FAIL extra LMB access" severity failure;
              assert M_ABus = EXPECTED_ADDR(access_index)
                report "AXI_LMB_SELF_CHECK_STATUS: FAIL LMB address mismatch" severity failure;
              assert M_ReadStrobe = std_logic'val(EXPECTED_READ(access_index)+2) and
                     M_WriteStrobe = std_logic'val(EXPECTED_WRITE(access_index)+2)
                report "AXI_LMB_SELF_CHECK_STATUS: FAIL LMB direction mismatch index=" &
                  integer'image(access_index) & " read=" & std_logic'image(M_ReadStrobe) &
                  " write=" & std_logic'image(M_WriteStrobe) & " expected_read=" &
                  integer'image(EXPECTED_READ(access_index)) & " expected_write=" &
                  integer'image(EXPECTED_WRITE(access_index)) severity failure;
              assert M_DBus = EXPECTED_DATA(access_index) and M_BE = EXPECTED_BE(access_index)
                report "AXI_LMB_SELF_CHECK_STATUS: FAIL LMB write payload mismatch" severity failure;
              access_index <= access_index + 1;
              read_data_now <= read_value(M_ABus);
              request_is_read <= M_ReadStrobe;
              responder_state <= WAITING;
            else
              responder_state <= IDLE;
            end if;
        end case;
      end if;
    end if;
  end process;

  stability_monitor : process(Clk)
    variable b_held, r_held : boolean := false;
    variable held_bid, held_rid : std_logic_vector(ID_WIDTH-1 downto 0);
    variable held_bresp, held_rresp : std_logic_vector(1 downto 0);
    variable held_rdata : std_logic_vector(DATA_WIDTH-1 downto 0);
    variable held_rlast : std_logic;
  begin
    if rising_edge(Clk) then
      if Rst = '1' then
        b_held := false; r_held := false;
        aw_handshakes <= 0; w_handshakes <= 0; wlast_handshakes <= 0;
      else
        if S_AXI_AWVALID = '1' and S_AXI_AWREADY = '1' then
          aw_handshakes <= aw_handshakes + 1;
        end if;
        if S_AXI_WVALID = '1' and S_AXI_WREADY = '1' then
          w_handshakes <= w_handshakes + 1;
          if S_AXI_WLAST = '1' then wlast_handshakes <= wlast_handshakes + 1; end if;
        end if;
        if b_held then
          assert S_AXI_BVALID = '1' and S_AXI_BID = held_bid and S_AXI_BRESP = held_bresp
            report "AXI_LMB_SELF_CHECK_STATUS: FAIL B changed under backpressure" severity failure;
        end if;
        if r_held then
          assert S_AXI_RVALID = '1' and S_AXI_RID = held_rid and
                 S_AXI_RDATA = held_rdata and S_AXI_RRESP = held_rresp and S_AXI_RLAST = held_rlast
            report "AXI_LMB_SELF_CHECK_STATUS: FAIL R changed under backpressure" severity failure;
        end if;
        b_held := S_AXI_BVALID = '1' and S_AXI_BREADY = '0';
        r_held := S_AXI_RVALID = '1' and S_AXI_RREADY = '0';
        if b_held then held_bid := S_AXI_BID; held_bresp := S_AXI_BRESP; end if;
        if r_held then
          held_rid := S_AXI_RID; held_rdata := S_AXI_RDATA;
          held_rresp := S_AXI_RRESP; held_rlast := S_AXI_RLAST;
        end if;
      end if;
    end if;
  end process;

  stimulus : process
    file output_file : text open write_mode is "<REPOSITORY_ROOT>/runs/framework/protocol_review/2026.1/2026-09-23_16-21-05_UTC+0800_3848c404/axi_lmb_bridge/frequency/actual.txt";
    variable row : line;

    procedure send_aw(ident : natural; address : std_logic_vector;
                      beats, size, burst, prot : natural) is
    begin
      S_AXI_AWID <= std_logic_vector(to_unsigned(ident, ID_WIDTH));
      S_AXI_AWADDR <= address;
      S_AXI_AWLEN <= std_logic_vector(to_unsigned(beats-1, 8));
      S_AXI_AWSIZE <= std_logic_vector(to_unsigned(size, 3));
      S_AXI_AWBURST <= std_logic_vector(to_unsigned(burst, 2));
      S_AXI_AWPROT <= std_logic_vector(to_unsigned(prot, 3));
      S_AXI_AWVALID <= '1';
      loop wait until rising_edge(Clk); exit when S_AXI_AWREADY = '1'; end loop;
      S_AXI_AWVALID <= '0';
    end procedure;

    procedure send_w(base : std_logic_vector; strobe, beat, beats : natural) is
    begin
      S_AXI_WDATA <= beat_value(base, beat);
      S_AXI_WSTRB <= std_logic_vector(to_unsigned(strobe, LANES));
      if beat = beats-1 then S_AXI_WLAST <= '1'; else S_AXI_WLAST <= '0'; end if;
      S_AXI_WVALID <= '1';
      loop wait until rising_edge(Clk); exit when S_AXI_WREADY = '1'; end loop;
      S_AXI_WVALID <= '0'; S_AXI_WLAST <= '0';
    end procedure;

    procedure drive_write(ident : natural; address : std_logic_vector;
                          beats, size, burst, prot, fault, waits, holds : natural;
                          base : std_logic_vector; strobe : natural; w_first : boolean) is
      variable zero_data : std_logic_vector(DATA_WIDTH-1 downto 0) := (others => '0');
    begin
      fault_mode <= fault; wait_limit <= waits;
      if w_first then
        for beat in 0 to beats-1 loop send_w(base, strobe, beat, beats); end loop;
        send_aw(ident, address, beats, size, burst, prot);
      else
        send_aw(ident, address, beats, size, burst, prot);
        for beat in 0 to beats-1 loop send_w(base, strobe, beat, beats); end loop;
      end if;
      loop wait until rising_edge(Clk); exit when S_AXI_BVALID = '1'; end loop;
      for i in 1 to holds loop wait until rising_edge(Clk); end loop;
      assert not is_x(S_AXI_BID) and not is_x(S_AXI_BRESP)
        report "AXI_LMB_SELF_CHECK_STATUS: FAIL unknown B response" severity failure;
      write_bit(row, '0'); write_bits(row, S_AXI_BID); write_bits(row, zero_data);
      write_bits(row, S_AXI_BRESP); write_bit(row, '0'); writeline(output_file, row);
      S_AXI_BREADY <= '1'; wait until rising_edge(Clk); S_AXI_BREADY <= '0';
    end procedure;

    procedure drive_read(ident : natural; address : std_logic_vector;
                         beats, size, burst, prot, fault, waits, holds : natural) is
    begin
      fault_mode <= fault; wait_limit <= waits;
      S_AXI_ARID <= std_logic_vector(to_unsigned(ident, ID_WIDTH));
      S_AXI_ARADDR <= address;
      S_AXI_ARLEN <= std_logic_vector(to_unsigned(beats-1, 8));
      S_AXI_ARSIZE <= std_logic_vector(to_unsigned(size, 3));
      S_AXI_ARBURST <= std_logic_vector(to_unsigned(burst, 2));
      S_AXI_ARPROT <= std_logic_vector(to_unsigned(prot, 3));
      S_AXI_ARVALID <= '1';
      loop wait until rising_edge(Clk); exit when S_AXI_ARREADY = '1'; end loop;
      S_AXI_ARVALID <= '0';
      for beat in 0 to beats-1 loop
        loop wait until rising_edge(Clk); exit when S_AXI_RVALID = '1'; end loop;
        for i in 1 to holds loop wait until rising_edge(Clk); end loop;
        assert not is_x(S_AXI_RID) and not is_x(S_AXI_RDATA) and
               not is_x(S_AXI_RRESP) and (S_AXI_RLAST = '0' or S_AXI_RLAST = '1')
          report "AXI_LMB_SELF_CHECK_STATUS: FAIL unknown R response" severity failure;
        write_bit(row, '1'); write_bits(row, S_AXI_RID); write_bits(row, S_AXI_RDATA);
        write_bits(row, S_AXI_RRESP); write_bit(row, S_AXI_RLAST); writeline(output_file, row);
        S_AXI_RREADY <= '1'; wait until rising_edge(Clk); S_AXI_RREADY <= '0';
      end loop;
    end procedure;
  begin
    for i in 1 to 6 loop wait until rising_edge(Clk); end loop;
    Rst <= '0';
    for i in 1 to 3 loop wait until rising_edge(Clk); end loop;
    drive_read(0, "00000000000000000000000011110000", 2, 2, 1, 0, 0, 0, 2);
    drive_read(0, "00000000000000000000001011000000", 1, 2, 1, 0, 2, 0, 0);
    drive_write(0, "00000000000000000000001011010000", 1, 2, 1, 0, 2, 0, 0, "00010010001101000101011001111000", 15, false);
    drive_write(0, "00000000000000000000001011100000", 1, 2, 1, 0, 0, 0, 0, "10000111011001010100001100100001", 15, false);
    drive_read(0, "00000000000000000000001011110000", 1, 2, 1, 0, 0, 0, 0);
    for i in 1 to 8 loop wait until rising_edge(Clk); end loop;
    assert access_index = ACCESS_COUNT
      report "AXI_LMB_SELF_CHECK_STATUS: FAIL missing LMB access" severity failure;
    report "AXI_LMB_SELF_CHECK_STATUS: PASS" severity failure;
    wait;
  end process;

  timeout : process
  begin
    wait for 10000 ns;
    report "AXI_LMB_SELF_CHECK_STATUS: FAIL timeout access_index=" &
      integer'image(access_index) & " awready=" & std_logic'image(S_AXI_AWREADY) &
      " wready=" & std_logic'image(S_AXI_WREADY) & " bvalid=" & std_logic'image(S_AXI_BVALID) &
      " arready=" & std_logic'image(S_AXI_ARREADY) & " rvalid=" & std_logic'image(S_AXI_RVALID) &
      " addrstrobe=" & std_logic'image(M_AddrStrobe) & " readstrobe=" &
      std_logic'image(M_ReadStrobe) & " writestrobe=" & std_logic'image(M_WriteStrobe) &
      " lmb_ready=" & std_logic'image(LMB_Ready) & " lmb_wait=" & std_logic'image(LMB_Wait)
      & " aw_handshakes=" & integer'image(aw_handshakes)
      & " w_handshakes=" & integer'image(w_handshakes)
      & " wlast_handshakes=" & integer'image(wlast_handshakes)
      severity failure;
  end process;
end architecture;

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;

entity tb_axi_protocol_converter is end entity;

architecture test of tb_axi_protocol_converter is
  constant DATA_WIDTH : positive := $data_width;
  constant ADDR_WIDTH : positive := $address_width;
  constant ID_WIDTH : positive := $id_width;
  constant LANES : positive := $lanes;
  constant ACCESS_COUNT : positive := $access_count;
  constant OPERATION_COUNT : positive := $operation_count;
  constant STALL_CYCLES : natural := $stall_cycles;
$declarations

  signal aclk : std_logic := '0';
  signal aresetn : std_logic := '0';
  signal s_axi_awid : std_logic_vector(ID_WIDTH-1 downto 0) := (others=>'0');
  signal s_axi_awaddr : std_logic_vector(ADDR_WIDTH-1 downto 0) := (others=>'0');
  signal s_axi_awlen : std_logic_vector(7 downto 0) := (others=>'0');
  signal s_axi_awsize : std_logic_vector(2 downto 0) := (others=>'0');
  signal s_axi_awburst : std_logic_vector(1 downto 0) := (others=>'0');
  signal s_axi_awlock : std_logic_vector(0 downto 0) := (others=>'0');
  signal s_axi_awcache, s_axi_awregion, s_axi_awqos : std_logic_vector(3 downto 0) := (others=>'0');
  signal s_axi_awprot : std_logic_vector(2 downto 0) := (others=>'0');
  signal s_axi_awvalid, s_axi_awready : std_logic := '0';
  signal s_axi_wdata : std_logic_vector(DATA_WIDTH-1 downto 0) := (others=>'0');
  signal s_axi_wstrb : std_logic_vector(LANES-1 downto 0) := (others=>'0');
  signal s_axi_wlast, s_axi_wvalid, s_axi_wready : std_logic := '0';
  signal s_axi_bid : std_logic_vector(ID_WIDTH-1 downto 0);
  signal s_axi_bresp : std_logic_vector(1 downto 0);
  signal s_axi_bvalid, s_axi_bready : std_logic := '0';
  signal s_axi_arid : std_logic_vector(ID_WIDTH-1 downto 0) := (others=>'0');
  signal s_axi_araddr : std_logic_vector(ADDR_WIDTH-1 downto 0) := (others=>'0');
  signal s_axi_arlen : std_logic_vector(7 downto 0) := (others=>'0');
  signal s_axi_arsize : std_logic_vector(2 downto 0) := (others=>'0');
  signal s_axi_arburst : std_logic_vector(1 downto 0) := (others=>'0');
  signal s_axi_arlock : std_logic_vector(0 downto 0) := (others=>'0');
  signal s_axi_arcache, s_axi_arregion, s_axi_arqos : std_logic_vector(3 downto 0) := (others=>'0');
  signal s_axi_arprot : std_logic_vector(2 downto 0) := (others=>'0');
  signal s_axi_arvalid, s_axi_arready : std_logic := '0';
  signal s_axi_rid : std_logic_vector(ID_WIDTH-1 downto 0);
  signal s_axi_rdata : std_logic_vector(DATA_WIDTH-1 downto 0);
  signal s_axi_rresp : std_logic_vector(1 downto 0);
  signal s_axi_rlast, s_axi_rvalid, s_axi_rready : std_logic := '0';

  signal m_axi_awaddr : std_logic_vector(ADDR_WIDTH-1 downto 0);
  signal m_axi_awprot : std_logic_vector(2 downto 0);
  signal m_axi_awvalid, m_axi_awready : std_logic := '0';
  signal m_axi_wdata : std_logic_vector(DATA_WIDTH-1 downto 0);
  signal m_axi_wstrb : std_logic_vector(LANES-1 downto 0);
  signal m_axi_wvalid, m_axi_wready : std_logic := '0';
  signal m_axi_bresp : std_logic_vector(1 downto 0) := (others=>'0');
  signal m_axi_bvalid, m_axi_bready : std_logic := '0';
  signal m_axi_araddr : std_logic_vector(ADDR_WIDTH-1 downto 0);
  signal m_axi_arprot : std_logic_vector(2 downto 0);
  signal m_axi_arvalid, m_axi_arready : std_logic := '0';
  signal m_axi_rdata : std_logic_vector(DATA_WIDTH-1 downto 0) := (others=>'0');
  signal m_axi_rresp : std_logic_vector(1 downto 0) := (others=>'0');
  signal m_axi_rvalid, m_axi_rready : std_logic := '0';
  signal access_index : natural range 0 to ACCESS_COUNT := 0;

  function beat_value(base : std_logic_vector; beat : natural) return std_logic_vector is
    variable result : unsigned(DATA_WIDTH-1 downto 0) := unsigned(base);
  begin
    result := result xor resize(to_unsigned(beat*257, 32), DATA_WIDTH);
    return std_logic_vector(result);
  end function;

  procedure write_bit(variable target : inout line; value : std_logic) is
  begin
    if value='1' then write(target, character'('1'));
    else write(target, character'('0')); end if;
  end procedure;

  procedure write_bits(variable target : inout line; value : std_logic_vector) is
  begin
    for index in value'range loop write_bit(target, value(index)); end loop;
  end procedure;
begin
  aclk <= not aclk after 5 ns;

  dut : entity work.dut_0 port map (
    aclk=>aclk, aresetn=>aresetn,
    s_axi_awid=>s_axi_awid, s_axi_awaddr=>s_axi_awaddr, s_axi_awlen=>s_axi_awlen,
    s_axi_awsize=>s_axi_awsize, s_axi_awburst=>s_axi_awburst, s_axi_awlock=>s_axi_awlock,
    s_axi_awcache=>s_axi_awcache, s_axi_awprot=>s_axi_awprot,
    s_axi_awregion=>s_axi_awregion, s_axi_awqos=>s_axi_awqos,
    s_axi_awvalid=>s_axi_awvalid, s_axi_awready=>s_axi_awready,
    s_axi_wdata=>s_axi_wdata, s_axi_wstrb=>s_axi_wstrb, s_axi_wlast=>s_axi_wlast,
    s_axi_wvalid=>s_axi_wvalid, s_axi_wready=>s_axi_wready,
    s_axi_bid=>s_axi_bid, s_axi_bresp=>s_axi_bresp,
    s_axi_bvalid=>s_axi_bvalid, s_axi_bready=>s_axi_bready,
    s_axi_arid=>s_axi_arid, s_axi_araddr=>s_axi_araddr, s_axi_arlen=>s_axi_arlen,
    s_axi_arsize=>s_axi_arsize, s_axi_arburst=>s_axi_arburst, s_axi_arlock=>s_axi_arlock,
    s_axi_arcache=>s_axi_arcache, s_axi_arprot=>s_axi_arprot,
    s_axi_arregion=>s_axi_arregion, s_axi_arqos=>s_axi_arqos,
    s_axi_arvalid=>s_axi_arvalid, s_axi_arready=>s_axi_arready,
    s_axi_rid=>s_axi_rid, s_axi_rdata=>s_axi_rdata, s_axi_rresp=>s_axi_rresp,
    s_axi_rlast=>s_axi_rlast, s_axi_rvalid=>s_axi_rvalid, s_axi_rready=>s_axi_rready,
    m_axi_awaddr=>m_axi_awaddr, m_axi_awprot=>m_axi_awprot,
    m_axi_awvalid=>m_axi_awvalid, m_axi_awready=>m_axi_awready,
    m_axi_wdata=>m_axi_wdata, m_axi_wstrb=>m_axi_wstrb,
    m_axi_wvalid=>m_axi_wvalid, m_axi_wready=>m_axi_wready,
    m_axi_bresp=>m_axi_bresp, m_axi_bvalid=>m_axi_bvalid, m_axi_bready=>m_axi_bready,
    m_axi_araddr=>m_axi_araddr, m_axi_arprot=>m_axi_arprot,
    m_axi_arvalid=>m_axi_arvalid, m_axi_arready=>m_axi_arready,
    m_axi_rdata=>m_axi_rdata, m_axi_rresp=>m_axi_rresp,
    m_axi_rvalid=>m_axi_rvalid, m_axi_rready=>m_axi_rready);

  axi_lite_responder : process(aclk)
    variable aw_seen, w_seen : boolean := false;
    variable aw_wait, w_wait, ar_wait : natural := 0;
  begin
    if rising_edge(aclk) then
      if aresetn='0' then
        m_axi_awready<='0'; m_axi_wready<='0'; m_axi_bvalid<='0';
        m_axi_arready<='0'; m_axi_rvalid<='0'; access_index<=0;
        aw_seen:=false; w_seen:=false; aw_wait:=0; w_wait:=0; ar_wait:=0;
      else
        if m_axi_bvalid='1' then
          if m_axi_bready='1' then
            m_axi_bvalid<='0'; access_index<=access_index+1;
            aw_seen:=false; w_seen:=false; aw_wait:=0; w_wait:=0;
          end if;
        else
          if not aw_seen then
            if m_axi_awvalid='1' and m_axi_awready='1' then
              assert access_index < ACCESS_COUNT and EXPECTED_KIND(access_index)=0
                report "AXI_PROTOCOL_CONVERTER_STATUS: FAIL unexpected AXI-Lite AW" severity failure;
              assert m_axi_awaddr=EXPECTED_ADDR(access_index) and m_axi_awprot=EXPECTED_PROT(access_index)
                report "AXI_PROTOCOL_CONVERTER_STATUS: FAIL AXI-Lite AW payload" severity failure;
              m_axi_awready<='0'; aw_seen:=true;
            elsif m_axi_awvalid='1' then
              if aw_wait >= STALL_CYCLES then m_axi_awready<='1';
              else aw_wait:=aw_wait+1; end if;
            else m_axi_awready<='0'; end if;
          end if;
          if not w_seen then
            if m_axi_wvalid='1' and m_axi_wready='1' then
              assert access_index < ACCESS_COUNT and EXPECTED_KIND(access_index)=0
                report "AXI_PROTOCOL_CONVERTER_STATUS: FAIL unexpected AXI-Lite W" severity failure;
              assert m_axi_wdata=EXPECTED_DATA(access_index) and
                     m_axi_wstrb=EXPECTED_STROBE(access_index)
                report "AXI_PROTOCOL_CONVERTER_STATUS: FAIL AXI-Lite W payload" severity failure;
              m_axi_wready<='0'; w_seen:=true;
            elsif m_axi_wvalid='1' then
              if w_wait >= STALL_CYCLES then m_axi_wready<='1';
              else w_wait:=w_wait+1; end if;
            else m_axi_wready<='0'; end if;
          end if;
          if aw_seen and w_seen then
            m_axi_bresp<=EXPECTED_RESPONSE(access_index); m_axi_bvalid<='1';
          end if;
        end if;

        if m_axi_rvalid='1' then
          if m_axi_rready='1' then
            m_axi_rvalid<='0'; access_index<=access_index+1; ar_wait:=0;
          end if;
        elsif m_axi_arvalid='1' and m_axi_arready='1' then
          assert access_index < ACCESS_COUNT and EXPECTED_KIND(access_index)=1
            report "AXI_PROTOCOL_CONVERTER_STATUS: FAIL unexpected AXI-Lite AR" severity failure;
          assert m_axi_araddr=EXPECTED_ADDR(access_index) and m_axi_arprot=EXPECTED_PROT(access_index)
            report "AXI_PROTOCOL_CONVERTER_STATUS: FAIL AXI-Lite AR payload" severity failure;
          m_axi_arready<='0'; m_axi_rdata<=EXPECTED_DATA(access_index);
          m_axi_rresp<=EXPECTED_RESPONSE(access_index); m_axi_rvalid<='1'; ar_wait:=0;
        elsif m_axi_arvalid='1' then
          if ar_wait >= STALL_CYCLES then m_axi_arready<='1';
          else ar_wait:=ar_wait+1; end if;
        else m_axi_arready<='0'; end if;
      end if;
    end if;
  end process;

  stability_monitor : process(aclk)
    variable saw, sw, sar, sb, sr : boolean := false;
    variable awaddr, araddr : std_logic_vector(ADDR_WIDTH-1 downto 0);
    variable awprot, arprot : std_logic_vector(2 downto 0);
    variable wdata, rdata : std_logic_vector(DATA_WIDTH-1 downto 0);
    variable wstrb : std_logic_vector(LANES-1 downto 0);
    variable bid, rid : std_logic_vector(ID_WIDTH-1 downto 0);
    variable bresp, rresp : std_logic_vector(1 downto 0);
    variable rlast : std_logic;
  begin
    if rising_edge(aclk) then
      if aresetn='0' then saw:=false; sw:=false; sar:=false; sb:=false; sr:=false;
      else
        if saw then assert m_axi_awvalid='1' and m_axi_awaddr=awaddr and m_axi_awprot=awprot
          report "AXI_PROTOCOL_CONVERTER_STATUS: FAIL AW changed under backpressure" severity failure; end if;
        if sw then assert m_axi_wvalid='1' and m_axi_wdata=wdata and m_axi_wstrb=wstrb
          report "AXI_PROTOCOL_CONVERTER_STATUS: FAIL W changed under backpressure" severity failure; end if;
        if sar then assert m_axi_arvalid='1' and m_axi_araddr=araddr and m_axi_arprot=arprot
          report "AXI_PROTOCOL_CONVERTER_STATUS: FAIL AR changed under backpressure" severity failure; end if;
        if sb then assert s_axi_bvalid='1' and s_axi_bid=bid and s_axi_bresp=bresp
          report "AXI_PROTOCOL_CONVERTER_STATUS: FAIL B changed under backpressure" severity failure; end if;
        if sr then assert s_axi_rvalid='1' and s_axi_rid=rid and s_axi_rdata=rdata and
          s_axi_rresp=rresp and s_axi_rlast=rlast
          report "AXI_PROTOCOL_CONVERTER_STATUS: FAIL R changed under backpressure" severity failure; end if;
        saw:=m_axi_awvalid='1' and m_axi_awready='0';
        sw:=m_axi_wvalid='1' and m_axi_wready='0';
        sar:=m_axi_arvalid='1' and m_axi_arready='0';
        sb:=s_axi_bvalid='1' and s_axi_bready='0';
        sr:=s_axi_rvalid='1' and s_axi_rready='0';
        if saw then awaddr:=m_axi_awaddr; awprot:=m_axi_awprot; end if;
        if sw then wdata:=m_axi_wdata; wstrb:=m_axi_wstrb; end if;
        if sar then araddr:=m_axi_araddr; arprot:=m_axi_arprot; end if;
        if sb then bid:=s_axi_bid; bresp:=s_axi_bresp; end if;
        if sr then rid:=s_axi_rid; rdata:=s_axi_rdata; rresp:=s_axi_rresp; rlast:=s_axi_rlast; end if;
      end if;
    end if;
  end process;

  stimulus : process
    file output_file : text open write_mode is "$output_path";
    variable row : line;
    variable zero_data : std_logic_vector(DATA_WIDTH-1 downto 0) := (others=>'0');
    procedure send_aw(ident : std_logic_vector; address : std_logic_vector;
                      beats, size, burst, prot : natural) is
    begin
      s_axi_awid<=ident; s_axi_awaddr<=address;
      s_axi_awlen<=std_logic_vector(to_unsigned(beats-1,8));
      s_axi_awsize<=std_logic_vector(to_unsigned(size,3));
      s_axi_awburst<=std_logic_vector(to_unsigned(burst,2));
      s_axi_awprot<=std_logic_vector(to_unsigned(prot,3)); s_axi_awvalid<='1';
      loop wait until rising_edge(aclk); exit when s_axi_awready='1'; end loop;
      s_axi_awvalid<='0';
    end procedure;
    procedure send_w(base : std_logic_vector; strobe, beat, beats : natural) is
    begin
      s_axi_wdata<=beat_value(base,beat); s_axi_wstrb<=std_logic_vector(to_unsigned(strobe,LANES));
      if beat=beats-1 then s_axi_wlast<='1'; else s_axi_wlast<='0'; end if;
      s_axi_wvalid<='1'; loop wait until rising_edge(aclk); exit when s_axi_wready='1'; end loop;
      s_axi_wvalid<='0'; s_axi_wlast<='0';
    end procedure;
    procedure drive_write(ident : std_logic_vector; address : std_logic_vector;
      beats, size, burst, prot, holds : natural; base : std_logic_vector;
      strobe : natural; w_first : boolean) is
    begin
      if w_first then
        for beat in 0 to beats-1 loop send_w(base,strobe,beat,beats); end loop;
        send_aw(ident,address,beats,size,burst,prot);
      else
        send_aw(ident,address,beats,size,burst,prot);
        for beat in 0 to beats-1 loop send_w(base,strobe,beat,beats); end loop;
      end if;
      loop wait until rising_edge(aclk); exit when s_axi_bvalid='1'; end loop;
      for i in 1 to holds loop wait until rising_edge(aclk); end loop;
      assert not is_x(s_axi_bid) and not is_x(s_axi_bresp)
        report "AXI_PROTOCOL_CONVERTER_STATUS: FAIL unknown B response" severity failure;
      write_bit(row,'0'); write_bits(row,s_axi_bid); write_bits(row,zero_data);
      write_bits(row,s_axi_bresp); write_bit(row,'0'); writeline(output_file,row);
      s_axi_bready<='1'; wait until rising_edge(aclk); s_axi_bready<='0';
    end procedure;
    procedure drive_read(ident : std_logic_vector; address : std_logic_vector;
      beats, size, burst, prot, holds : natural) is
    begin
      s_axi_arid<=ident; s_axi_araddr<=address;
      s_axi_arlen<=std_logic_vector(to_unsigned(beats-1,8));
      s_axi_arsize<=std_logic_vector(to_unsigned(size,3));
      s_axi_arburst<=std_logic_vector(to_unsigned(burst,2));
      s_axi_arprot<=std_logic_vector(to_unsigned(prot,3)); s_axi_arvalid<='1';
      loop wait until rising_edge(aclk); exit when s_axi_arready='1'; end loop;
      s_axi_arvalid<='0';
      for beat in 0 to beats-1 loop
        loop wait until rising_edge(aclk); exit when s_axi_rvalid='1'; end loop;
        for i in 1 to holds loop wait until rising_edge(aclk); end loop;
        assert not is_x(s_axi_rid) and not is_x(s_axi_rdata) and not is_x(s_axi_rresp)
          report "AXI_PROTOCOL_CONVERTER_STATUS: FAIL unknown R response" severity failure;
        write_bit(row,'1'); write_bits(row,s_axi_rid); write_bits(row,s_axi_rdata);
        write_bits(row,s_axi_rresp); write_bit(row,s_axi_rlast); writeline(output_file,row);
        s_axi_rready<='1'; wait until rising_edge(aclk); s_axi_rready<='0';
      end loop;
    end procedure;
  begin
    for i in 1 to 6 loop wait until rising_edge(aclk); end loop;
    aresetn<='1'; for i in 1 to 5 loop wait until rising_edge(aclk); end loop;
$operation_calls
    for i in 1 to 8 loop wait until rising_edge(aclk); end loop;
    assert access_index=ACCESS_COUNT
      report "AXI_PROTOCOL_CONVERTER_STATUS: FAIL missing AXI-Lite access" severity failure;
    report "AXI_PROTOCOL_CONVERTER_STATUS: PASS" severity failure;
    wait;
  end process;

  timeout : process
  begin
    wait for $timeout_ns ns;
    report "AXI_PROTOCOL_CONVERTER_STATUS: FAIL timeout access_index=" &
      integer'image(access_index) severity failure;
  end process;
end architecture;

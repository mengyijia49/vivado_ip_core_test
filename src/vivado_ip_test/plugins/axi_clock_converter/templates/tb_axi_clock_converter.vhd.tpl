library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;

entity tb_axi_clock_converter is end entity;

architecture test of tb_axi_clock_converter is
  constant DATA_WIDTH : positive := $data_width;
  constant ADDR_WIDTH : positive := $address_width;
  constant ID_WIDTH : positive := $id_width;
  constant USER_WIDTH : positive := $user_width;
  constant LANES : positive := $lanes;
  constant OPERATION_COUNT : positive := $operation_count;
  signal s_axi_aclk : std_logic := '0';
  signal m_axi_aclk : std_logic := '0';
  signal s_axi_aresetn, m_axi_aresetn : std_logic := '0';

  signal s_axi_awid, m_axi_awid : std_logic_vector(ID_WIDTH-1 downto 0) := (others => '0');
  signal s_axi_awaddr, m_axi_awaddr : std_logic_vector(ADDR_WIDTH-1 downto 0) := (others => '0');
  signal s_axi_awlen, m_axi_awlen : std_logic_vector(7 downto 0) := (others => '0');
  signal s_axi_awsize, m_axi_awsize : std_logic_vector(2 downto 0) := (others => '0');
  signal s_axi_awburst, m_axi_awburst : std_logic_vector(1 downto 0) := (others => '0');
  signal s_axi_awlock, m_axi_awlock : std_logic_vector(0 downto 0) := (others => '0');
  signal s_axi_awcache, m_axi_awcache : std_logic_vector(3 downto 0) := (others => '0');
  signal s_axi_awprot, m_axi_awprot : std_logic_vector(2 downto 0) := (others => '0');
  signal s_axi_awregion, m_axi_awregion, s_axi_awqos, m_axi_awqos : std_logic_vector(3 downto 0) := (others => '0');
  signal s_axi_awuser, m_axi_awuser : std_logic_vector(USER_WIDTH-1 downto 0) := (others => '0');
  signal s_axi_awvalid, s_axi_awready, m_axi_awvalid, m_axi_awready : std_logic := '0';

  signal s_axi_wdata, m_axi_wdata : std_logic_vector(DATA_WIDTH-1 downto 0) := (others => '0');
  signal s_axi_wstrb, m_axi_wstrb : std_logic_vector(LANES-1 downto 0) := (others => '0');
  signal s_axi_wlast, m_axi_wlast : std_logic := '0';
  signal s_axi_wuser, m_axi_wuser : std_logic_vector(USER_WIDTH-1 downto 0) := (others => '0');
  signal s_axi_wvalid, s_axi_wready, m_axi_wvalid, m_axi_wready : std_logic := '0';

  signal s_axi_bid, m_axi_bid : std_logic_vector(ID_WIDTH-1 downto 0) := (others => '0');
  signal s_axi_bresp, m_axi_bresp : std_logic_vector(1 downto 0) := (others => '0');
  signal s_axi_buser, m_axi_buser : std_logic_vector(USER_WIDTH-1 downto 0) := (others => '0');
  signal s_axi_bvalid, s_axi_bready, m_axi_bvalid, m_axi_bready : std_logic := '0';

  signal s_axi_arid, m_axi_arid : std_logic_vector(ID_WIDTH-1 downto 0) := (others => '0');
  signal s_axi_araddr, m_axi_araddr : std_logic_vector(ADDR_WIDTH-1 downto 0) := (others => '0');
  signal s_axi_arlen, m_axi_arlen : std_logic_vector(7 downto 0) := (others => '0');
  signal s_axi_arsize, m_axi_arsize : std_logic_vector(2 downto 0) := (others => '0');
  signal s_axi_arburst, m_axi_arburst : std_logic_vector(1 downto 0) := (others => '0');
  signal s_axi_arlock, m_axi_arlock : std_logic_vector(0 downto 0) := (others => '0');
  signal s_axi_arcache, m_axi_arcache : std_logic_vector(3 downto 0) := (others => '0');
  signal s_axi_arprot, m_axi_arprot : std_logic_vector(2 downto 0) := (others => '0');
  signal s_axi_arregion, m_axi_arregion, s_axi_arqos, m_axi_arqos : std_logic_vector(3 downto 0) := (others => '0');
  signal s_axi_aruser, m_axi_aruser : std_logic_vector(USER_WIDTH-1 downto 0) := (others => '0');
  signal s_axi_arvalid, s_axi_arready, m_axi_arvalid, m_axi_arready : std_logic := '0';

  signal s_axi_rid, m_axi_rid : std_logic_vector(ID_WIDTH-1 downto 0) := (others => '0');
  signal s_axi_rdata, m_axi_rdata : std_logic_vector(DATA_WIDTH-1 downto 0) := (others => '0');
  signal s_axi_rresp, m_axi_rresp : std_logic_vector(1 downto 0) := (others => '0');
  signal s_axi_rlast, m_axi_rlast : std_logic := '0';
  signal s_axi_ruser, m_axi_ruser : std_logic_vector(USER_WIDTH-1 downto 0) := (others => '0');
  signal s_axi_rvalid, s_axi_rready, m_axi_rvalid, m_axi_rready : std_logic := '0';

  function zero_vector(width : positive) return std_logic_vector is
  begin return std_logic_vector(to_unsigned(0, width)); end function;
begin
  s_axi_aclk <= not s_axi_aclk after 5 ns;
  m_axi_aclk <= not m_axi_aclk after $output_half_period ns;

  dut : entity work.dut_0 port map (
    s_axi_aclk=>s_axi_aclk, s_axi_aresetn=>s_axi_aresetn,
    m_axi_aclk=>m_axi_aclk, m_axi_aresetn=>m_axi_aresetn,
    s_axi_awid=>s_axi_awid, s_axi_awaddr=>s_axi_awaddr, s_axi_awlen=>s_axi_awlen,
    s_axi_awsize=>s_axi_awsize, s_axi_awburst=>s_axi_awburst, s_axi_awlock=>s_axi_awlock,
    s_axi_awcache=>s_axi_awcache, s_axi_awprot=>s_axi_awprot, s_axi_awregion=>s_axi_awregion,
    s_axi_awqos=>s_axi_awqos, s_axi_awuser=>s_axi_awuser, s_axi_awvalid=>s_axi_awvalid,
    s_axi_awready=>s_axi_awready, m_axi_awid=>m_axi_awid, m_axi_awaddr=>m_axi_awaddr,
    m_axi_awlen=>m_axi_awlen, m_axi_awsize=>m_axi_awsize, m_axi_awburst=>m_axi_awburst,
    m_axi_awlock=>m_axi_awlock, m_axi_awcache=>m_axi_awcache, m_axi_awprot=>m_axi_awprot,
    m_axi_awregion=>m_axi_awregion, m_axi_awqos=>m_axi_awqos, m_axi_awuser=>m_axi_awuser,
    m_axi_awvalid=>m_axi_awvalid, m_axi_awready=>m_axi_awready,
    s_axi_wdata=>s_axi_wdata, s_axi_wstrb=>s_axi_wstrb, s_axi_wlast=>s_axi_wlast,
    s_axi_wuser=>s_axi_wuser, s_axi_wvalid=>s_axi_wvalid, s_axi_wready=>s_axi_wready,
    m_axi_wdata=>m_axi_wdata, m_axi_wstrb=>m_axi_wstrb, m_axi_wlast=>m_axi_wlast,
    m_axi_wuser=>m_axi_wuser, m_axi_wvalid=>m_axi_wvalid, m_axi_wready=>m_axi_wready,
    s_axi_bid=>s_axi_bid, s_axi_bresp=>s_axi_bresp, s_axi_buser=>s_axi_buser,
    s_axi_bvalid=>s_axi_bvalid, s_axi_bready=>s_axi_bready, m_axi_bid=>m_axi_bid,
    m_axi_bresp=>m_axi_bresp, m_axi_buser=>m_axi_buser, m_axi_bvalid=>m_axi_bvalid,
    m_axi_bready=>m_axi_bready,
    s_axi_arid=>s_axi_arid, s_axi_araddr=>s_axi_araddr, s_axi_arlen=>s_axi_arlen,
    s_axi_arsize=>s_axi_arsize, s_axi_arburst=>s_axi_arburst, s_axi_arlock=>s_axi_arlock,
    s_axi_arcache=>s_axi_arcache, s_axi_arprot=>s_axi_arprot, s_axi_arregion=>s_axi_arregion,
    s_axi_arqos=>s_axi_arqos, s_axi_aruser=>s_axi_aruser, s_axi_arvalid=>s_axi_arvalid,
    s_axi_arready=>s_axi_arready, m_axi_arid=>m_axi_arid, m_axi_araddr=>m_axi_araddr,
    m_axi_arlen=>m_axi_arlen, m_axi_arsize=>m_axi_arsize, m_axi_arburst=>m_axi_arburst,
    m_axi_arlock=>m_axi_arlock, m_axi_arcache=>m_axi_arcache, m_axi_arprot=>m_axi_arprot,
    m_axi_arregion=>m_axi_arregion, m_axi_arqos=>m_axi_arqos, m_axi_aruser=>m_axi_aruser,
    m_axi_arvalid=>m_axi_arvalid, m_axi_arready=>m_axi_arready,
    s_axi_rid=>s_axi_rid, s_axi_rdata=>s_axi_rdata, s_axi_rresp=>s_axi_rresp,
    s_axi_rlast=>s_axi_rlast, s_axi_ruser=>s_axi_ruser, s_axi_rvalid=>s_axi_rvalid,
    s_axi_rready=>s_axi_rready, m_axi_rid=>m_axi_rid, m_axi_rdata=>m_axi_rdata,
    m_axi_rresp=>m_axi_rresp, m_axi_rlast=>m_axi_rlast, m_axi_ruser=>m_axi_ruser,
    m_axi_rvalid=>m_axi_rvalid, m_axi_rready=>m_axi_rready);

  stimulus : process
    file output_file : text open write_mode is "$output_path";
    variable row : line;
    procedure write_bit(value : std_logic) is
    begin if value='1' then write(row, character'('1')); else write(row, character'('0')); end if; end;
    procedure write_bits(value : std_logic_vector) is
    begin for i in value'range loop write_bit(value(i)); end loop; end;
    procedure record_row(channel : natural; ident, addr, lenv, sizev, burstv : std_logic_vector;
      lockv : std_logic; cachev, protv, regionv, qosv, datav, strbv : std_logic_vector;
      lastv : std_logic; respv, userv : std_logic_vector) is
    begin
      write_bits(std_logic_vector(to_unsigned(channel,3))); write_bits(ident); write_bits(addr);
      write_bits(lenv); write_bits(sizev); write_bits(burstv); write_bit(lockv); write_bits(cachev);
      write_bits(protv); write_bits(regionv); write_bits(qosv); write_bits(datav); write_bits(strbv);
      write_bit(lastv); write_bits(respv); write_bits(userv); writeline(output_file,row);
    end;
    procedure drive(channel : natural; ident : std_logic_vector(ID_WIDTH-1 downto 0);
      addr : std_logic_vector(ADDR_WIDTH-1 downto 0); lenv : std_logic_vector(7 downto 0);
      sizev : std_logic_vector(2 downto 0); burstv : std_logic_vector(1 downto 0);
      lockv : std_logic; cachev : std_logic_vector(3 downto 0); protv : std_logic_vector(2 downto 0);
      regionv, qosv : std_logic_vector(3 downto 0); datav : std_logic_vector(DATA_WIDTH-1 downto 0);
      strbv : std_logic_vector(LANES-1 downto 0); lastv : std_logic;
      respv : std_logic_vector(1 downto 0); userv : std_logic_vector(USER_WIDTH-1 downto 0);
      holds : natural) is
      variable zi : std_logic_vector(ID_WIDTH-1 downto 0) := (others=>'0');
      variable za : std_logic_vector(ADDR_WIDTH-1 downto 0) := (others=>'0');
      variable zd : std_logic_vector(DATA_WIDTH-1 downto 0) := (others=>'0');
      variable zs : std_logic_vector(LANES-1 downto 0) := (others=>'0');
      variable zu : std_logic_vector(USER_WIDTH-1 downto 0) := (others=>'0');
    begin
      case channel is
        when 0 =>
          s_axi_awid<=ident; s_axi_awaddr<=addr; s_axi_awlen<=lenv; s_axi_awsize<=sizev;
          s_axi_awburst<=burstv; s_axi_awlock(0)<=lockv; s_axi_awcache<=cachev; s_axi_awprot<=protv;
          s_axi_awregion<=regionv; s_axi_awqos<=qosv; s_axi_awuser<=userv; s_axi_awvalid<='1';
          loop wait until rising_edge(s_axi_aclk); exit when s_axi_awready='1'; end loop;
          s_axi_awvalid<='0'; loop wait until rising_edge(m_axi_aclk); exit when m_axi_awvalid='1'; end loop;
          for i in 1 to holds loop wait until rising_edge(m_axi_aclk); assert m_axi_awvalid='1' report "AXI_CLOCK_CONVERTER_STATUS: FAIL AW dropped under backpressure" severity failure; end loop;
          assert m_axi_awid=ident and m_axi_awaddr=addr and m_axi_awlen=lenv and m_axi_awsize=sizev and
            m_axi_awburst=burstv and m_axi_awlock(0)=lockv and m_axi_awcache=cachev and m_axi_awprot=protv and
            m_axi_awregion=regionv and m_axi_awqos=qosv and m_axi_awuser=userv
            report "AXI_CLOCK_CONVERTER_STATUS: FAIL AW payload" severity failure;
          record_row(0,m_axi_awid,m_axi_awaddr,m_axi_awlen,m_axi_awsize,m_axi_awburst,m_axi_awlock(0),
            m_axi_awcache,m_axi_awprot,m_axi_awregion,m_axi_awqos,zd,zs,'0',"00",m_axi_awuser);
          m_axi_awready<='1'; wait until rising_edge(m_axi_aclk); m_axi_awready<='0';
        when 1 =>
          s_axi_wdata<=datav; s_axi_wstrb<=strbv; s_axi_wlast<=lastv; s_axi_wuser<=userv; s_axi_wvalid<='1';
          loop wait until rising_edge(s_axi_aclk); exit when s_axi_wready='1'; end loop; s_axi_wvalid<='0';
          loop wait until rising_edge(m_axi_aclk); exit when m_axi_wvalid='1'; end loop;
          for i in 1 to holds loop wait until rising_edge(m_axi_aclk); assert m_axi_wvalid='1' report "AXI_CLOCK_CONVERTER_STATUS: FAIL W dropped under backpressure" severity failure; end loop;
          assert m_axi_wdata=datav and m_axi_wstrb=strbv and m_axi_wlast=lastv and m_axi_wuser=userv
            report "AXI_CLOCK_CONVERTER_STATUS: FAIL W payload" severity failure;
          record_row(1,zi,za,x"00","000","00",'0',"0000","000","0000","0000",
            m_axi_wdata,m_axi_wstrb,m_axi_wlast,"00",m_axi_wuser);
          m_axi_wready<='1'; wait until rising_edge(m_axi_aclk); m_axi_wready<='0';
        when 2 =>
          m_axi_bid<=ident; m_axi_bresp<=respv; m_axi_buser<=userv; m_axi_bvalid<='1';
          loop wait until rising_edge(m_axi_aclk); exit when m_axi_bready='1'; end loop; m_axi_bvalid<='0';
          loop wait until rising_edge(s_axi_aclk); exit when s_axi_bvalid='1'; end loop;
          for i in 1 to holds loop wait until rising_edge(s_axi_aclk); assert s_axi_bvalid='1' report "AXI_CLOCK_CONVERTER_STATUS: FAIL B dropped under backpressure" severity failure; end loop;
          assert s_axi_bid=ident and s_axi_bresp=respv and s_axi_buser=userv report "AXI_CLOCK_CONVERTER_STATUS: FAIL B payload" severity failure;
          record_row(2,s_axi_bid,za,x"00","000","00",'0',"0000","000","0000","0000",zd,zs,'0',s_axi_bresp,s_axi_buser);
          s_axi_bready<='1'; wait until rising_edge(s_axi_aclk); s_axi_bready<='0';
        when 3 =>
          s_axi_arid<=ident; s_axi_araddr<=addr; s_axi_arlen<=lenv; s_axi_arsize<=sizev;
          s_axi_arburst<=burstv; s_axi_arlock(0)<=lockv; s_axi_arcache<=cachev; s_axi_arprot<=protv;
          s_axi_arregion<=regionv; s_axi_arqos<=qosv; s_axi_aruser<=userv; s_axi_arvalid<='1';
          loop wait until rising_edge(s_axi_aclk); exit when s_axi_arready='1'; end loop; s_axi_arvalid<='0';
          loop wait until rising_edge(m_axi_aclk); exit when m_axi_arvalid='1'; end loop;
          for i in 1 to holds loop wait until rising_edge(m_axi_aclk); assert m_axi_arvalid='1' report "AXI_CLOCK_CONVERTER_STATUS: FAIL AR dropped under backpressure" severity failure; end loop;
          assert m_axi_arid=ident and m_axi_araddr=addr and m_axi_arlen=lenv and m_axi_arsize=sizev and
            m_axi_arburst=burstv and m_axi_arlock(0)=lockv and m_axi_arcache=cachev and m_axi_arprot=protv and
            m_axi_arregion=regionv and m_axi_arqos=qosv and m_axi_aruser=userv
            report "AXI_CLOCK_CONVERTER_STATUS: FAIL AR payload" severity failure;
          record_row(3,m_axi_arid,m_axi_araddr,m_axi_arlen,m_axi_arsize,m_axi_arburst,m_axi_arlock(0),
            m_axi_arcache,m_axi_arprot,m_axi_arregion,m_axi_arqos,zd,zs,'0',"00",m_axi_aruser);
          m_axi_arready<='1'; wait until rising_edge(m_axi_aclk); m_axi_arready<='0';
        when others =>
          m_axi_rid<=ident; m_axi_rdata<=datav; m_axi_rresp<=respv; m_axi_rlast<=lastv;
          m_axi_ruser<=userv; m_axi_rvalid<='1';
          loop wait until rising_edge(m_axi_aclk); exit when m_axi_rready='1'; end loop; m_axi_rvalid<='0';
          loop wait until rising_edge(s_axi_aclk); exit when s_axi_rvalid='1'; end loop;
          for i in 1 to holds loop wait until rising_edge(s_axi_aclk); assert s_axi_rvalid='1' report "AXI_CLOCK_CONVERTER_STATUS: FAIL R dropped under backpressure" severity failure; end loop;
          assert s_axi_rid=ident and s_axi_rdata=datav and s_axi_rresp=respv and s_axi_rlast=lastv and s_axi_ruser=userv
            report "AXI_CLOCK_CONVERTER_STATUS: FAIL R payload" severity failure;
          record_row(4,s_axi_rid,za,x"00","000","00",'0',"0000","000","0000","0000",
            s_axi_rdata,zs,s_axi_rlast,s_axi_rresp,s_axi_ruser);
          s_axi_rready<='1'; wait until rising_edge(s_axi_aclk); s_axi_rready<='0';
      end case;
    end;
  begin
    wait for 100 ns; wait until falling_edge(s_axi_aclk); s_axi_aresetn<='1';
    wait until falling_edge(m_axi_aclk); m_axi_aresetn<='1'; wait for 100 ns;
$operation_calls
    wait for 100 ns;
    report "AXI_CLOCK_CONVERTER_STATUS: PASS" severity failure;
    wait;
  end process;

  timeout : process
  begin wait for $timeout_ns ns; report "AXI_CLOCK_CONVERTER_STATUS: FAIL timeout" severity failure; end process;
end architecture;

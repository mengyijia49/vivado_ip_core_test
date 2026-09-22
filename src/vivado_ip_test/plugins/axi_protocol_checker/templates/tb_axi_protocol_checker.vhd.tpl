library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;

entity tb_axi_protocol_checker is end entity;

architecture test of tb_axi_protocol_checker is
  constant DATA_WIDTH : positive := $data_width;
  constant ADDR_WIDTH : positive := $address_width;
  constant ID_WIDTH : positive := $id_width;
  constant LANES : positive := DATA_WIDTH/8;
  constant DATA_SIZE : natural := $data_size;

  signal aclk : std_logic := '0';
  signal aresetn : std_logic := '0';
  signal pc_status : std_logic_vector(159 downto 0);
  signal pc_asserted : std_logic;
  signal awid : std_logic_vector(ID_WIDTH-1 downto 0) := (others=>'0');
  signal awaddr : std_logic_vector(ADDR_WIDTH-1 downto 0) := (others=>'0');
  signal awlen : std_logic_vector(7 downto 0) := (others=>'0');
  signal awsize : std_logic_vector(2 downto 0) := std_logic_vector(to_unsigned(DATA_SIZE,3));
  signal awburst : std_logic_vector(1 downto 0) := "01";
  signal awlock : std_logic_vector(0 downto 0) := "0";
  signal awcache : std_logic_vector(3 downto 0) := "0011";
  signal awprot : std_logic_vector(2 downto 0) := (others=>'0');
  signal awqos, awregion : std_logic_vector(3 downto 0) := (others=>'0');
  signal awvalid, awready : std_logic := '0';
  signal wlast : std_logic := '0';
  signal wdata : std_logic_vector(DATA_WIDTH-1 downto 0) := (others=>'0');
  signal wstrb : std_logic_vector(LANES-1 downto 0) := (others=>'1');
  signal wvalid, wready : std_logic := '0';
  signal bid : std_logic_vector(ID_WIDTH-1 downto 0) := (others=>'0');
  signal bresp : std_logic_vector(1 downto 0) := (others=>'0');
  signal bvalid, bready : std_logic := '0';
  signal arid : std_logic_vector(ID_WIDTH-1 downto 0) := (others=>'0');
  signal araddr : std_logic_vector(ADDR_WIDTH-1 downto 0) := (others=>'0');
  signal arlen : std_logic_vector(7 downto 0) := (others=>'0');
  signal arsize : std_logic_vector(2 downto 0) := std_logic_vector(to_unsigned(DATA_SIZE,3));
  signal arburst : std_logic_vector(1 downto 0) := "01";
  signal arlock : std_logic_vector(0 downto 0) := "0";
  signal arcache : std_logic_vector(3 downto 0) := "0011";
  signal arprot : std_logic_vector(2 downto 0) := (others=>'0');
  signal arqos, arregion : std_logic_vector(3 downto 0) := (others=>'0');
  signal arvalid, arready : std_logic := '0';
  signal rid : std_logic_vector(ID_WIDTH-1 downto 0) := (others=>'0');
  signal rlast : std_logic := '0';
  signal rdata : std_logic_vector(DATA_WIDTH-1 downto 0) := (others=>'0');
  signal rresp : std_logic_vector(1 downto 0) := (others=>'0');
  signal rvalid, rready : std_logic := '0';

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
    pc_status=>pc_status, pc_asserted=>pc_asserted, aclk=>aclk, aresetn=>aresetn,
    pc_axi_awid=>awid, pc_axi_awaddr=>awaddr, pc_axi_awlen=>awlen,
    pc_axi_awsize=>awsize, pc_axi_awburst=>awburst, pc_axi_awlock=>awlock,
    pc_axi_awcache=>awcache, pc_axi_awprot=>awprot, pc_axi_awqos=>awqos,
    pc_axi_awregion=>awregion, pc_axi_awvalid=>awvalid, pc_axi_awready=>awready,
    pc_axi_wlast=>wlast, pc_axi_wdata=>wdata, pc_axi_wstrb=>wstrb,
    pc_axi_wvalid=>wvalid, pc_axi_wready=>wready, pc_axi_bid=>bid,
    pc_axi_bresp=>bresp, pc_axi_bvalid=>bvalid, pc_axi_bready=>bready,
    pc_axi_arid=>arid, pc_axi_araddr=>araddr, pc_axi_arlen=>arlen,
    pc_axi_arsize=>arsize, pc_axi_arburst=>arburst, pc_axi_arlock=>arlock,
    pc_axi_arcache=>arcache, pc_axi_arprot=>arprot, pc_axi_arqos=>arqos,
    pc_axi_arregion=>arregion, pc_axi_arvalid=>arvalid, pc_axi_arready=>arready,
    pc_axi_rid=>rid, pc_axi_rlast=>rlast, pc_axi_rdata=>rdata,
    pc_axi_rresp=>rresp, pc_axi_rvalid=>rvalid, pc_axi_rready=>rready);

  stimulus : process
    file output_file : text open write_mode is "$output_path";
    variable row : line;

    procedure idle_bus is
    begin
      awid<=(others=>'0'); awaddr<=(others=>'0'); awlen<=(others=>'0');
      awsize<=std_logic_vector(to_unsigned(DATA_SIZE,3)); awburst<="01";
      awlock<="0"; awcache<="0011"; awprot<=(others=>'0');
      awqos<=(others=>'0'); awregion<=(others=>'0'); awvalid<='0'; awready<='0';
      wlast<='0'; wdata<=(others=>'0'); wstrb<=(others=>'1'); wvalid<='0'; wready<='0';
      bid<=(others=>'0'); bresp<="00"; bvalid<='0'; bready<='0';
      arid<=(others=>'0'); araddr<=(others=>'0'); arlen<=(others=>'0');
      arsize<=std_logic_vector(to_unsigned(DATA_SIZE,3)); arburst<="01";
      arlock<="0"; arcache<="0011"; arprot<=(others=>'0');
      arqos<=(others=>'0'); arregion<=(others=>'0'); arvalid<='0'; arready<='0';
      rid<=(others=>'0'); rlast<='0'; rdata<=(others=>'0'); rresp<="00";
      rvalid<='0'; rready<='0';
    end procedure;

    procedure reset_checker is
    begin
      idle_bus; aresetn<='0';
      for i in 1 to 4 loop wait until rising_edge(aclk); end loop;
      aresetn<='1';
      for i in 1 to 3 loop wait until rising_edge(aclk); end loop;
      assert pc_status=(pc_status'range=>'0') and pc_asserted='0'
        report "AXI_PROTOCOL_CHECKER_STATUS: FAIL reset did not clear status" severity failure;
    end procedure;

    procedure legal_transaction(ident : std_logic_vector; address : std_logic_vector;
                                value : std_logic_vector) is
    begin
      awid<=ident; awaddr<=address; awvalid<='1'; awready<='1';
      wait until rising_edge(aclk); awvalid<='0'; awready<='0';
      wdata<=value; wlast<='1'; wvalid<='1'; wready<='1';
      wait until rising_edge(aclk); wvalid<='0'; wready<='0'; wlast<='0';
      bid<=ident; bvalid<='1'; bready<='1';
      wait until rising_edge(aclk); bvalid<='0'; bready<='0';
      arid<=ident; araddr<=address; arvalid<='1'; arready<='1';
      wait until rising_edge(aclk); arvalid<='0'; arready<='0';
      rid<=ident; rdata<=value; rlast<='1'; rvalid<='1'; rready<='1';
      wait until rising_edge(aclk); rvalid<='0'; rready<='0'; rlast<='0';
    end procedure;

    procedure run_case(scenario : natural; ident : std_logic_vector;
                       address : std_logic_vector; value : std_logic_vector) is
    begin
      reset_checker;
      awid<=ident; awaddr<=address; wdata<=value;
      arid<=ident; araddr<=address; rdata<=value;
      case scenario is
        when 0 => legal_transaction(ident,address,value);
        when 1 =>
          awburst<="11"; awvalid<='1'; awready<='1';
          wait until rising_edge(aclk); awvalid<='0'; awready<='0';
        when 2 =>
          awburst<="10"; awlen<=std_logic_vector(to_unsigned(2,8));
          awvalid<='1'; awready<='1'; wait until rising_edge(aclk);
          awvalid<='0'; awready<='0';
        when 3 =>
          $aw_width_violation
          awvalid<='1'; awready<='1'; wait until rising_edge(aclk);
          awvalid<='0'; awready<='0';
        when 4 =>
          awvalid<='1'; awready<='0'; wait until rising_edge(aclk);
          awvalid<='0'; wait until rising_edge(aclk);
        when 5 =>
          awvalid<='1'; awready<='0';
          for i in 1 to 2 loop wait until rising_edge(aclk); end loop;
          awaddr<=std_logic_vector(unsigned(address)+4);
          for i in 1 to 2 loop wait until rising_edge(aclk); end loop;
          awready<='1'; wait until rising_edge(aclk); awvalid<='0'; awready<='0';
        when 6 =>
          arburst<="11"; arvalid<='1'; arready<='1';
          wait until rising_edge(aclk); arvalid<='0'; arready<='0';
        when 7 =>
          arburst<="10"; arlen<=std_logic_vector(to_unsigned(2,8));
          arvalid<='1'; arready<='1'; wait until rising_edge(aclk);
          arvalid<='0'; arready<='0';
        when 8 =>
          $ar_width_violation
          arvalid<='1'; arready<='1'; wait until rising_edge(aclk);
          arvalid<='0'; arready<='0';
        when 9 =>
          arvalid<='1'; arready<='0'; wait until rising_edge(aclk);
          arvalid<='0'; wait until rising_edge(aclk);
        when 10 =>
          arvalid<='1'; arready<='0';
          for i in 1 to 2 loop wait until rising_edge(aclk); end loop;
          araddr<=std_logic_vector(unsigned(address)+4);
          for i in 1 to 2 loop wait until rising_edge(aclk); end loop;
          arready<='1'; wait until rising_edge(aclk); arvalid<='0'; arready<='0';
        when others =>
          report "AXI_PROTOCOL_CHECKER_STATUS: FAIL unknown scenario" severity failure;
      end case;
      for i in 1 to 5 loop wait until rising_edge(aclk); end loop;
      wait until falling_edge(aclk);
      assert not is_x(pc_status) and not is_x(pc_asserted)
        report "AXI_PROTOCOL_CHECKER_STATUS: FAIL unknown checker output" severity failure;
      if pc_status=(pc_status'range=>'0') then
        assert pc_asserted='0'
          report "AXI_PROTOCOL_CHECKER_STATUS: FAIL pc_asserted without status" severity failure;
      else
        assert pc_asserted='1'
          report "AXI_PROTOCOL_CHECKER_STATUS: FAIL missing pc_asserted" severity failure;
      end if;
      write_bits(row,pc_status); writeline(output_file,row);
    end procedure;
  begin
$operation_calls
    report "AXI_PROTOCOL_CHECKER_STATUS: PASS" severity failure;
    wait;
  end process;

  timeout : process
  begin
    wait for $timeout_ns ns;
    report "AXI_PROTOCOL_CHECKER_STATUS: FAIL timeout" severity failure;
  end process;
end architecture;

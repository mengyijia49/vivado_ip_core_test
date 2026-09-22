library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;
use std.env.all;

entity tb_ahblite_axi_bridge is end entity;

architecture sim of tb_ahblite_axi_bridge is
  constant DATA_WIDTH : positive := $data_width;
  constant ADDR_WIDTH : positive := $address_width;
  constant ID_WIDTH : positive := $id_width;
  constant LANES : positive := $lanes;
  constant STALL_CYCLES : natural := $stall_cycles;
  constant RESPONSE_DELAY : natural := $response_delay;
  constant OPERATION_COUNT : positive := $operation_count;
  signal clk : std_logic := '0';
$signals
  signal operation_active : std_logic := '0';
  signal expected_address : std_logic_vector(ADDR_WIDTH-1 downto 0) := (others=>'0');
  signal expected_data : std_logic_vector(DATA_WIDTH-1 downto 0) := (others=>'0');
  signal expected_strobe : std_logic_vector(LANES-1 downto 0) := (others=>'0');
  signal expected_size : std_logic_vector(2 downto 0) := (others=>'0');
  signal expected_prot : std_logic_vector(2 downto 0) := (others=>'0');
  signal expected_cache : std_logic_vector(3 downto 0) := (others=>'0');
  signal expected_response : std_logic_vector(1 downto 0) := (others=>'0');
  signal expected_write : std_logic := '0';
  signal observed_address : std_logic_vector(ADDR_WIDTH-1 downto 0) := (others=>'0');
  signal observed_data : std_logic_vector(DATA_WIDTH-1 downto 0) := (others=>'0');
  signal observed_strobe : std_logic_vector(LANES-1 downto 0) := (others=>'0');
  signal completed_count : natural range 0 to OPERATION_COUNT := 0;

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
  clk <= not clk after 5 ns;
  s_ahb_hready_in <= s_ahb_hready_out;

  dut : entity work.dut_0 port map (
      $mappings);

  axi_responder : process(clk)
    variable cycle, response_wait : natural := 0;
    variable aw_seen, w_seen, ar_seen : boolean := false;
  begin
    if rising_edge(clk) then
      if s_ahb_hresetn='0' then
        cycle:=0; response_wait:=0; aw_seen:=false; w_seen:=false; ar_seen:=false;
        m_axi_awready<='0'; m_axi_wready<='0'; m_axi_arready<='0';
        m_axi_bvalid<='0'; m_axi_rvalid<='0'; completed_count<=0;
      else
        cycle:=cycle+1;
        if STALL_CYCLES=0 or cycle mod (STALL_CYCLES+3) >= STALL_CYCLES then
          m_axi_awready<='1'; m_axi_arready<='1';
        else m_axi_awready<='0'; m_axi_arready<='0'; end if;
        if STALL_CYCLES=0 or cycle mod (STALL_CYCLES+5) >= STALL_CYCLES then
          m_axi_wready<='1';
        else m_axi_wready<='0'; end if;

        if m_axi_awvalid='1' and m_axi_awready='1' then
          assert operation_active='1' and expected_write='1' and m_axi_awaddr=expected_address
            and m_axi_awid=(m_axi_awid'range=>'0') and m_axi_awlen=x"00"
            and m_axi_awsize=expected_size and m_axi_awburst="01" and m_axi_awlock='0'
            and m_axi_awprot=expected_prot and m_axi_awcache=expected_cache
            report "AHBLITE_AXI_STATUS: FAIL AW" severity failure;
          observed_address<=m_axi_awaddr; aw_seen:=true;
        end if;
        if m_axi_wvalid='1' and m_axi_wready='1' then
          assert operation_active='1' and expected_write='1' and m_axi_wdata=expected_data
            and m_axi_wstrb=expected_strobe and m_axi_wlast='1'
            report "AHBLITE_AXI_STATUS: FAIL W" severity failure;
          observed_data<=m_axi_wdata; observed_strobe<=m_axi_wstrb; w_seen:=true;
        end if;
        if m_axi_bvalid='1' and m_axi_bready='1' then
          m_axi_bvalid<='0'; aw_seen:=false; w_seen:=false; response_wait:=0;
          completed_count<=completed_count+1;
        elsif aw_seen and w_seen then
          if response_wait >= RESPONSE_DELAY then
            m_axi_bid<=(others=>'0'); m_axi_bresp<=expected_response; m_axi_bvalid<='1';
          else response_wait:=response_wait+1; end if;
        end if;

        if m_axi_arvalid='1' and m_axi_arready='1' then
          assert operation_active='1' and expected_write='0' and m_axi_araddr=expected_address
            and m_axi_arid=(m_axi_arid'range=>'0') and m_axi_arlen=x"00"
            and m_axi_arsize=expected_size and m_axi_arburst="01" and m_axi_arlock='0'
            and m_axi_arprot=expected_prot and m_axi_arcache=expected_cache
            report "AHBLITE_AXI_STATUS: FAIL AR" severity failure;
          observed_address<=m_axi_araddr; ar_seen:=true;
        end if;
        if m_axi_rvalid='1' and m_axi_rready='1' then
          m_axi_rvalid<='0'; ar_seen:=false; response_wait:=0;
          completed_count<=completed_count+1;
        elsif ar_seen then
          if response_wait >= RESPONSE_DELAY then
            m_axi_rid<=(others=>'0'); m_axi_rdata<=expected_data;
            m_axi_rresp<=expected_response; m_axi_rlast<='1'; m_axi_rvalid<='1';
          else response_wait:=response_wait+1; end if;
        end if;
      end if;
    end if;
  end process;

  stimulus : process
    file actual_file : text open write_mode is "$output_path";
    variable output_line : line;

    procedure start_transfer(index : natural; address : std_logic_vector;
        size : natural; hprot, prot, cache, response : std_logic_vector;
        write_access : std_logic; data : std_logic_vector; strobe : std_logic_vector) is
    begin
      wait until falling_edge(clk);
      expected_address<=address; expected_size<=std_logic_vector(to_unsigned(size,3));
      expected_prot<=prot; expected_cache<=cache; expected_response<=response;
      expected_write<=write_access; expected_data<=data; expected_strobe<=strobe;
      operation_active<='1';
      s_ahb_hsel<='1'; s_ahb_haddr<=address; s_ahb_hprot<=hprot;
      s_ahb_htrans<="10"; s_ahb_hsize<=std_logic_vector(to_unsigned(size,3));
      s_ahb_hwrite<=write_access; s_ahb_hburst<="000"; s_ahb_hwdata<=data;
      wait until rising_edge(clk);
      wait until falling_edge(clk);
      s_ahb_hsel<='0'; s_ahb_htrans<="00";
      loop
        wait until rising_edge(clk); wait for 1 ps;
        exit when completed_count=index+1 and s_ahb_hready_out='1';
      end loop;
      if response/="00" then
        assert s_ahb_hresp='1' report "AHBLITE_AXI_STATUS: FAIL HRESP" severity failure;
      else
        assert s_ahb_hresp='0' report "AHBLITE_AXI_STATUS: FAIL HRESP" severity failure;
      end if;
    end procedure;

    procedure save_result(write_access : std_logic; data, strobe : std_logic_vector) is
    begin
      write_bit(output_line,write_access); write_bits(output_line,observed_address);
      write_bits(output_line,data); write_bits(output_line,strobe);
      write_bit(output_line,s_ahb_hresp); writeline(actual_file,output_line);
      operation_active<='0';
    end procedure;

    procedure run_write(index : natural; address : std_logic_vector; size : natural;
        hprot, prot, cache, response : std_logic_vector; data, strobe : std_logic_vector) is
    begin
      start_transfer(index,address,size,hprot,prot,cache,response,'1',data,strobe);
      save_result('1',observed_data,observed_strobe);
    end procedure;

    procedure run_read(index : natural; address : std_logic_vector; size : natural;
        hprot, prot, cache, response : std_logic_vector; data : std_logic_vector) is
    begin
      start_transfer(index,address,size,hprot,prot,cache,response,'0',data,(LANES-1 downto 0=>'0'));
      assert s_ahb_hrdata=data report "AHBLITE_AXI_STATUS: FAIL HRDATA" severity failure;
      save_result('0',s_ahb_hrdata,(LANES-1 downto 0=>'0'));
    end procedure;
  begin
    s_ahb_hresetn<='0'; s_ahb_hsel<='0'; s_ahb_htrans<="00";
    wait for 50 ns; wait until rising_edge(clk); s_ahb_hresetn<='1';
    wait until rising_edge(clk);
$operation_calls
    flush(actual_file);
    assert completed_count=OPERATION_COUNT
      report "AHBLITE_AXI_STATUS: FAIL operation count" severity failure;
    report "AHBLITE_AXI_STATUS: PASS"; finish; wait;
  end process;

  watchdog : process
  begin
    wait for $timeout_ns ns;
    assert false report "AHBLITE_AXI_STATUS: FAIL timeout" severity failure;
    wait;
  end process;
end architecture;

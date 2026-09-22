library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;
use std.env.all;

entity tb_axi_memory_init is end entity;

architecture sim of tb_axi_memory_init is
  constant DATA_WIDTH : positive := $data_width;
  constant ADDR_WIDTH : positive := $address_width;
  constant ID_WIDTH : positive := $id_width;
  constant LANES : positive := $lanes;
  constant BEAT_COUNT : positive := $beat_count;
  constant BURST_COUNT : positive := $burst_count;
  constant DATA_SIZE : natural := $data_size;
  constant PAUSE_CYCLES : natural := $pause_cycles;
  constant STALL_CYCLES : natural := $stall_cycles;
  constant RESPONSE_DELAY : natural := $response_delay;
  constant BASE_ADDR : unsigned(ADDR_WIDTH-1 downto 0) := unsigned'("$base_bits");
  constant INIT_VALUE : std_logic_vector(DATA_WIDTH-1 downto 0) := "$init_bits";
  constant POST_VALUE : std_logic_vector(DATA_WIDTH-1 downto 0) := "$post_bits";
  signal aclk : std_logic := '0';
$signals

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
      $mappings);

  stimulus_and_responder : process
    file actual_file : text open write_mode is "$output_path";
    variable output_line : line;
    variable cycle, aw_count, w_count, pending_b, delay_count : natural := 0;
    variable expected_address : unsigned(ADDR_WIDTH-1 downto 0);
    variable last_seen : boolean;
  begin
    init_complete_in <= '1';
    aclken <= '0';
    aresetn <= '0';
    wait for 40 ns;
    wait until rising_edge(aclk);
    aresetn <= '1';
    for index in 1 to PAUSE_CYCLES loop
      wait until rising_edge(aclk);
    end loop;
    aclken <= '1';

    while w_count < BEAT_COUNT or aw_count < BURST_COUNT or pending_b > 0 loop
      cycle := cycle + 1;
      assert cycle <= BEAT_COUNT*20+1000
        report "AXI_MEMORY_INIT_STATUS: FAIL responder stalled aw=" & integer'image(aw_count) &
          " w=" & integer'image(w_count) & " pending_b=" & integer'image(pending_b)
        severity failure;
      if STALL_CYCLES=0 or cycle mod (STALL_CYCLES+3) >= STALL_CYCLES then
        m_axi_awready <= '1';
      else m_axi_awready <= '0'; end if;
      if STALL_CYCLES=0 or cycle mod (STALL_CYCLES+5) >= STALL_CYCLES then
        m_axi_wready <= '1';
      else m_axi_wready <= '0'; end if;

      if pending_b > 0 and delay_count >= RESPONSE_DELAY then
        m_axi_bvalid <= '1';
      else m_axi_bvalid <= '0'; end if;
      m_axi_bid <= (others=>'0'); m_axi_bresp <= "00";
      wait until rising_edge(aclk);

      if m_axi_awvalid='1' and m_axi_awready='1' then
        expected_address := BASE_ADDR + to_unsigned(aw_count*16*LANES, ADDR_WIDTH);
        assert unsigned(m_axi_awaddr)=expected_address and m_axi_awid=(m_axi_awid'range=>'0')
          and unsigned(m_axi_awlen)=15 and unsigned(m_axi_awsize)=DATA_SIZE
          and m_axi_awburst="01" and m_axi_awlock="0" and m_axi_awcache="0000"
          and m_axi_awprot="000" and m_axi_awqos="0000" and m_axi_awregion="0000"
          report "AXI_MEMORY_INIT_STATUS: FAIL initialization AW" severity failure;
        aw_count := aw_count+1;
      end if;
      last_seen := false;
      if m_axi_wvalid='1' and m_axi_wready='1' then
        assert m_axi_wdata=INIT_VALUE and m_axi_wstrb=(m_axi_wstrb'range=>'1')
          and ((w_count mod 16=15 and m_axi_wlast='1') or
               (w_count mod 16/=15 and m_axi_wlast='0'))
          report "AXI_MEMORY_INIT_STATUS: FAIL initialization W" severity failure;
        write_bits(output_line, m_axi_wdata); write_bits(output_line, m_axi_wstrb);
        write_bit(output_line, m_axi_wlast); writeline(actual_file, output_line);
        last_seen := m_axi_wlast='1';
        w_count := w_count+1;
      end if;
      if m_axi_bvalid='1' and m_axi_bready='1' then
        pending_b := pending_b-1; delay_count := 0;
      elsif pending_b > 0 then delay_count := delay_count+1; end if;
      if last_seen then pending_b := pending_b+1; end if;
      assert aw_count <= BURST_COUNT and w_count <= BEAT_COUNT
        report "AXI_MEMORY_INIT_STATUS: FAIL too many initialization transfers" severity failure;
    end loop;
    m_axi_awready<='0'; m_axi_wready<='0'; m_axi_bvalid<='0';
    for index in 0 to 20 loop
      wait until rising_edge(aclk); wait for 1 ps;
      exit when init_complete_out='1';
    end loop;
    assert init_complete_out='1' and aw_count=BURST_COUNT and w_count=BEAT_COUNT
      report "AXI_MEMORY_INIT_STATUS: FAIL completion" severity failure;

    s_axi_awid <= std_logic_vector(to_unsigned(1,ID_WIDTH));
    s_axi_awaddr <= std_logic_vector(BASE_ADDR+to_unsigned(16#80#,ADDR_WIDTH));
    s_axi_awlen<=x"03"; s_axi_awsize<=std_logic_vector(to_unsigned(DATA_SIZE,3));
    s_axi_awburst<="01"; s_axi_awlock<="1"; s_axi_awcache<="1010";
    s_axi_awprot<="101"; s_axi_awqos<="0110"; s_axi_awregion<="1001"; s_axi_awvalid<='1';
    s_axi_wdata<=POST_VALUE; s_axi_wstrb<=(others=>'1'); s_axi_wstrb(0)<='0';
    s_axi_wlast<='1'; s_axi_wvalid<='1'; s_axi_bready<='1';
    s_axi_arid<=(others=>'0');
    s_axi_araddr<=std_logic_vector(BASE_ADDR+to_unsigned(16#100#,ADDR_WIDTH));
    s_axi_arlen<=x"01"; s_axi_arsize<=std_logic_vector(to_unsigned(DATA_SIZE,3));
    s_axi_arburst<="10"; s_axi_arlock<="0"; s_axi_arcache<="0101";
    s_axi_arprot<="011"; s_axi_arqos<="1001"; s_axi_arregion<="0011"; s_axi_arvalid<='1';
    s_axi_rready<='1';
    m_axi_bid<=std_logic_vector(to_unsigned(1,ID_WIDTH)); m_axi_bresp<="10"; m_axi_bvalid<='1';
    m_axi_rid<=(others=>'0'); m_axi_rdata<=POST_VALUE;
    m_axi_rresp<="01"; m_axi_rlast<='1'; m_axi_rvalid<='1';
    wait for 1 ns;
    assert m_axi_awid=s_axi_awid and m_axi_awaddr=s_axi_awaddr and m_axi_awlen=s_axi_awlen
      and m_axi_awsize=s_axi_awsize and m_axi_awburst=s_axi_awburst and m_axi_awlock=s_axi_awlock
      and m_axi_awcache=s_axi_awcache and m_axi_awprot=s_axi_awprot and m_axi_awqos=s_axi_awqos
      and m_axi_awregion=s_axi_awregion and m_axi_awvalid='1' and s_axi_awready='0'
      report "AXI_MEMORY_INIT_STATUS: FAIL post-init AW" severity failure;
    assert m_axi_wdata=POST_VALUE and m_axi_wstrb=s_axi_wstrb and m_axi_wlast='1'
      and m_axi_wvalid='1' and s_axi_wready='0'
      report "AXI_MEMORY_INIT_STATUS: FAIL post-init W" severity failure;
    assert s_axi_bid=m_axi_bid and s_axi_bresp="10" and s_axi_bvalid='1' and m_axi_bready='1'
      report "AXI_MEMORY_INIT_STATUS: FAIL post-init B" severity failure;
    assert m_axi_arid=s_axi_arid and m_axi_araddr=s_axi_araddr and m_axi_arlen=s_axi_arlen
      and m_axi_arsize=s_axi_arsize and m_axi_arburst=s_axi_arburst and m_axi_arlock=s_axi_arlock
      and m_axi_arcache=s_axi_arcache and m_axi_arprot=s_axi_arprot and m_axi_arqos=s_axi_arqos
      and m_axi_arregion=s_axi_arregion and m_axi_arvalid='1' and s_axi_arready='0'
      report "AXI_MEMORY_INIT_STATUS: FAIL post-init AR" severity failure;
    assert s_axi_rid=m_axi_rid and s_axi_rdata=POST_VALUE and s_axi_rresp="01"
      and s_axi_rlast='1' and s_axi_rvalid='1' and m_axi_rready='1'
      report "AXI_MEMORY_INIT_STATUS: FAIL post-init R" severity failure;
    write_bits(output_line,m_axi_wdata); write_bits(output_line,m_axi_wstrb);
    write_bit(output_line,m_axi_wlast); writeline(actual_file,output_line); flush(actual_file);
    report "AXI_MEMORY_INIT_STATUS: PASS"; finish; wait;
  end process;

  watchdog : process
  begin
    wait for $timeout_ns ns;
    assert false report "AXI_MEMORY_INIT_STATUS: FAIL timeout" severity failure;
    wait;
  end process;
end architecture;

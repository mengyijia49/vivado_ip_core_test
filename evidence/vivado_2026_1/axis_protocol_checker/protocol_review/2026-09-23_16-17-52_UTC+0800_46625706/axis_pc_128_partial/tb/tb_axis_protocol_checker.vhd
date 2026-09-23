library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;

entity tb_axis_protocol_checker is end entity;

architecture test of tb_axis_protocol_checker is
  constant DATA_WIDTH : positive := 128;
  constant LANES : positive := 16;
  constant ID_WIDTH : positive := 1;
  constant DEST_WIDTH : positive := 8;
  constant USER_WIDTH : positive := 16;
  constant MAX_WAITS : natural := 64;

  signal aclk : std_logic := '0';
  signal aresetn, system_resetn : std_logic := '0';
  signal aclken : std_logic := '1';
  signal tvalid, tready, tlast : std_logic := '0';
  signal tdata : std_logic_vector(DATA_WIDTH-1 downto 0) := (others=>'0');
  signal tstrb, tkeep : std_logic_vector(LANES-1 downto 0) := (others=>'1');
  signal tid : std_logic_vector(ID_WIDTH-1 downto 0) := (others=>'0');
  signal tdest : std_logic_vector(DEST_WIDTH-1 downto 0) := (others=>'0');
  signal tuser : std_logic_vector(USER_WIDTH-1 downto 0) := (others=>'0');
  signal pc_asserted : std_logic;
  signal pc_status : std_logic_vector(31 downto 0);

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
    pc_axis_tvalid=>tvalid, pc_axis_tdata=>tdata,
    pc_asserted=>pc_asserted, pc_status=>pc_status,
    pc_axis_tready=>tready,
    pc_axis_tkeep=>tkeep,
    pc_axis_tlast=>tlast,
    pc_axis_tdest=>tdest,
    pc_axis_tuser=>tuser);

  stimulus : process
    file output_file : text open write_mode is "<REPOSITORY_ROOT>/runs/batches/2026.1/2026-09-23_16-17-52_UTC+0800_46625706/axis_protocol_checker/axis_pc_128_partial/outputs/actual_output.txt";
    variable row : line;

    procedure idle_stream is
    begin
      tvalid<='0'; tready<='0'; tlast<='0'; tdata<=(others=>'0');
      tstrb<=(others=>'1'); tkeep<=(others=>'1');
      tid<=(others=>'0'); tdest<=(others=>'0'); tuser<=(others=>'0');
      aclken<='1';
    end procedure;

    procedure reset_checker is
    begin
      idle_stream; aresetn<='0'; system_resetn<='0';
      for i in 1 to 4 loop wait until rising_edge(aclk); end loop;
      system_resetn<='1'; aresetn<='1';
      for i in 1 to 6 loop wait until rising_edge(aclk); end loop;
      wait until falling_edge(aclk);
      assert pc_status=(pc_status'range=>'0') and pc_asserted='0'
        report "AXIS_PROTOCOL_CHECKER_STATUS: FAIL reset did not clear status" severity failure;
    end procedure;

    procedure establish_stall is
    begin
      tvalid<='1'; tready<='0';
      for i in 1 to 2 loop wait until rising_edge(aclk); end loop;
    end procedure;

    procedure finish_stall is
    begin
      for i in 1 to 2 loop wait until rising_edge(aclk); end loop;
      tready<='1';
      wait until rising_edge(aclk);
      idle_stream;
    end procedure;

    procedure run_case(scenario : natural) is
    begin
      reset_checker;
      case scenario is
        when 0 =>
          tvalid<='1'; tready<='1'; tlast<='1';
          tdata<=std_logic_vector(to_unsigned(16#5A#,DATA_WIDTH));
          wait until rising_edge(aclk); idle_stream;
        when 1 =>
          aresetn<='0'; system_resetn<='0'; tvalid<='1';
          for i in 1 to 3 loop wait until rising_edge(aclk); end loop;
          system_resetn<='1'; aresetn<='1';
          for i in 1 to 6 loop wait until rising_edge(aclk); end loop;
          tready<='1'; wait until rising_edge(aclk); tvalid<='0'; tready<='0';
        when 2 =>
          establish_stall; tid<=std_logic_vector(unsigned(tid)+1); finish_stall;
        when 3 =>
          establish_stall; tdest<=std_logic_vector(unsigned(tdest)+1); finish_stall;
        when 4 =>
          tkeep<=(others=>'0'); tstrb<=(others=>'0');
          establish_stall; tkeep(0)<='1'; finish_stall;
        when 5 =>
          establish_stall; tdata(0)<=not tdata(0); finish_stall;
        when 6 =>
          establish_stall; tlast<=not tlast; finish_stall;
        when 7 =>
          establish_stall; tstrb(0)<=not tstrb(0); finish_stall;
        when 8 =>
          establish_stall; tvalid<='0';
          for i in 1 to 3 loop wait until rising_edge(aclk); end loop;
        when 9 =>
          tvalid<='1'; tready<='0';
          for i in 1 to MAX_WAITS+4 loop wait until rising_edge(aclk); end loop;
          tready<='1'; wait until rising_edge(aclk); idle_stream;
        when 10 =>
          establish_stall; tuser(0)<=not tuser(0); finish_stall;
        when 11 =>
          tvalid<='1'; tready<='1'; tkeep<=(others=>'0'); tstrb<=(others=>'0');
          tstrb(0)<='1';
          for i in 1 to 2 loop wait until rising_edge(aclk); end loop;
          idle_stream;
        when 12 =>
          tvalid<='1'; tready<='0'; aclken<='0';
          for i in 1 to MAX_WAITS+4 loop wait until rising_edge(aclk); end loop;
          tready<='1'; aclken<='1'; wait until rising_edge(aclk); idle_stream;
        when others =>
          report "AXIS_PROTOCOL_CHECKER_STATUS: FAIL unknown scenario" severity failure;
      end case;
      for i in 1 to 8 loop wait until rising_edge(aclk); end loop;
      wait until falling_edge(aclk);
      assert not is_x(pc_status) and not is_x(pc_asserted)
        report "AXIS_PROTOCOL_CHECKER_STATUS: FAIL unknown checker output" severity failure;
      if pc_status=(pc_status'range=>'0') then
        assert pc_asserted='0'
          report "AXIS_PROTOCOL_CHECKER_STATUS: FAIL asserted without status" severity failure;
      else
        assert pc_asserted='1'
          report "AXIS_PROTOCOL_CHECKER_STATUS: FAIL missing asserted output" severity failure;
      end if;
      write_bits(row,pc_status); writeline(output_file,row);
    end procedure;
  begin
    run_case(0);
    run_case(1);
    run_case(5);
    run_case(8);
    run_case(3);
    run_case(4);
    run_case(6);
    run_case(10);
    run_case(9);
    run_case(0);
    run_case(1);
    run_case(5);
    run_case(8);
    run_case(3);
    run_case(4);
    run_case(6);
    run_case(10);
    run_case(9);
    run_case(0);
    run_case(1);
    run_case(5);
    run_case(8);
    run_case(3);
    run_case(4);
    report "AXIS_PROTOCOL_CHECKER_STATUS: PASS" severity failure;
    wait;
  end process;

  timeout : process
  begin
    wait for 32560 ns;
    report "AXIS_PROTOCOL_CHECKER_STATUS: FAIL timeout" severity failure;
  end process;
end architecture;

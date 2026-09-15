library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (
    aclk, aresetn : in std_logic;
    s_axis_a_tdata, s_axis_b_tdata, s_axis_operation_tdata : in std_logic_vector(7 downto 0);
    s_axis_a_tuser : in std_logic_vector(2 downto 0);
    s_axis_b_tuser : in std_logic_vector(4 downto 0);
    s_axis_operation_tuser : in std_logic_vector(1 downto 0);
    s_axis_a_tvalid, s_axis_b_tvalid, s_axis_operation_tvalid : in std_logic;
    s_axis_a_tlast, s_axis_b_tlast, s_axis_operation_tlast : in std_logic;
    s_axis_a_tready, s_axis_b_tready, s_axis_operation_tready : out std_logic;
    m_axis_result_tdata : out std_logic_vector(7 downto 0);
    m_axis_result_tuser : out std_logic_vector(12 downto 0);
    m_axis_result_tvalid, m_axis_result_tlast : out std_logic;
    m_axis_result_tready : in std_logic
  );
end entity;

architecture fixture of dut_0 is
  type data_queue is array(0 to 3) of std_logic_vector(7 downto 0);
  type user_queue is array(0 to 3) of std_logic_vector(9 downto 0);
  type last_queue is array(0 to 3) of std_logic;
  signal qa, qb, qo : data_queue := (others => (others => '0'));
  signal ua, ub, uo : user_queue := (others => (others => '0'));
  signal la, lb, lo : last_queue := (others => '0');
  signal wa, wb, wo, rd : natural := 0;
  signal ready_a, ready_b, ready_o, valid, extra, toggle, was_stalled : std_logic := '0';
begin
  ready_a <= '1' when aresetn = '1' and wa - rd < 4 else '0';
  ready_b <= '1' when aresetn = '1' and wb - rd < 4 else '0';
  ready_o <= '1' when aresetn = '1' and wo - rd < 4 else '0';
  s_axis_a_tready <= 'X' when fault_mode = 10 else ready_a;
  s_axis_b_tready <= ready_b;
  s_axis_operation_tready <= ready_o;
  valid <= '1' when aresetn = '1' and wa > rd and wb > rd and wo > rd else '0';
  m_axis_result_tvalid <= '0' when fault_mode = 6 or (fault_mode = 9 and was_stalled = '1') else
                         '1' when fault_mode = 8 and aresetn = '1' else valid or extra;
  process(aclk)
  begin
    if rising_edge(aclk) then
      if aresetn = '0' then
        wa <= 0; wb <= 0; wo <= 0; rd <= 0;
        extra <= '0'; toggle <= '0'; was_stalled <= '0';
      else
        toggle <= not toggle;
        was_stalled <= valid and not m_axis_result_tready;
        if s_axis_a_tvalid = '1' and ready_a = '1' then
          qa(wa mod 4) <= s_axis_a_tdata;
          ua(wa mod 4) <= std_logic_vector(resize(unsigned(s_axis_a_tuser), 10));
          la(wa mod 4) <= s_axis_a_tlast;
          wa <= wa + 1;
        end if;
        if s_axis_b_tvalid = '1' and ready_b = '1' and fault_mode /= 13 then
          qb(wb mod 4) <= s_axis_b_tdata;
          ub(wb mod 4) <= std_logic_vector(resize(unsigned(s_axis_b_tuser), 10));
          lb(wb mod 4) <= s_axis_b_tlast;
          wb <= wb + 1;
        end if;
        if s_axis_operation_tvalid = '1' and ready_o = '1' then
          qo(wo mod 4) <= s_axis_operation_tdata;
          uo(wo mod 4) <= std_logic_vector(resize(unsigned(s_axis_operation_tuser), 10));
          lo(wo mod 4) <= s_axis_operation_tlast;
          wo <= wo + 1;
        end if;
        if valid = '1' and m_axis_result_tready = '1' then
          rd <= rd + 1;
          if fault_mode = 7 and rd = 11 then extra <= '1'; end if;
        elsif extra = '1' and m_axis_result_tready = '1' then
          extra <= '0';
        end if;
      end if;
    end if;
  end process;
  process(all)
    variable value : std_logic_vector(7 downto 0);
    variable users : std_logic_vector(9 downto 0);
    variable ending : std_logic;
    variable flags : std_logic_vector(2 downto 0);
    variable key : std_logic_vector(21 downto 0);
  begin
    key := qa(rd mod 4) & qb(rd mod 4) & qo(rd mod 4)(5 downto 0);
    value := x"00";
    flags := "000";
    case key is
      when x"0080" & "000000" | x"3838" & "000001" => value := x"00";
      when x"8080" & "000000" => value := x"80";
      when x"3818" & "000000" => value := x"38";
      when x"3918" & "000000" => value := x"3A";
      when x"3F18" & "000000" => value := x"40";
      when x"7777" & "000000" => value := x"78"; flags := "010";
      when x"0908" & "000001" => value := x"00"; flags := "001";
      when x"78F8" & "000000" | x"7878" & "000001" => value := x"7C"; flags := "100";
      when x"7938" & "000000" => value := x"7C";
      when x"01B8" & "000000" => value := x"B8";
      when others => value := (others => 'X');
    end case;
    users := uo(rd mod 4)(1 downto 0) & ub(rd mod 4)(4 downto 0) & ua(rd mod 4)(2 downto 0);
    ending := la(rd mod 4) or lb(rd mod 4) or lo(rd mod 4);
    if fault_mode = 1 then value(0) := not value(0); end if;
    if fault_mode = 2 then users(0) := not users(0); end if;
    if fault_mode = 3 then ending := not ending; end if;
    if fault_mode = 4 then value(0) := 'X'; end if;
    if fault_mode = 5 then value(0) := value(0) xor toggle; end if;
    if fault_mode = 11 then value(0) := qo(rd mod 4)(0); end if;
    if fault_mode = 12 then flags(0) := not flags(0); end if;
    m_axis_result_tdata <= value;
    m_axis_result_tuser <= users & flags;
    m_axis_result_tlast <= ending;
  end process;
end architecture;

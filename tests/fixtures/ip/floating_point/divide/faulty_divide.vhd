library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (
    aclk, aresetn : in std_logic;
    s_axis_a_tdata, s_axis_b_tdata : in std_logic_vector(31 downto 0);
    s_axis_a_tuser : in std_logic_vector(2 downto 0);
    s_axis_b_tuser : in std_logic_vector(4 downto 0);
    s_axis_a_tvalid, s_axis_b_tvalid, s_axis_a_tlast, s_axis_b_tlast : in std_logic;
    s_axis_a_tready, s_axis_b_tready : out std_logic;
    m_axis_result_tdata : out std_logic_vector(31 downto 0);
    m_axis_result_tuser : out std_logic_vector(11 downto 0);
    m_axis_result_tvalid, m_axis_result_tlast : out std_logic;
    m_axis_result_tready : in std_logic
  );
end entity;

architecture fixture of dut_0 is
  type data_queue is array(0 to 3) of std_logic_vector(31 downto 0);
  type user_queue is array(0 to 3) of std_logic_vector(7 downto 0);
  type last_queue is array(0 to 3) of std_logic;
  signal qa, qb : data_queue := (others => (others => '0'));
  signal ua, ub : user_queue := (others => (others => '0'));
  signal la, lb : last_queue := (others => '0');
  signal wa, wb, rd : natural := 0;
  signal ready_a, ready_b, valid, extra, toggle, was_stalled : std_logic := '0';
begin
  ready_a <= '1' when aresetn = '1' and wa - rd < 4 else '0';
  ready_b <= '1' when aresetn = '1' and wb - rd < 4 else '0';
  s_axis_a_tready <= 'X' when fault_mode = 10 else ready_a;
  s_axis_b_tready <= ready_b;
  valid <= '1' when aresetn = '1' and wa > rd and wb > rd else '0';
  m_axis_result_tvalid <= '0' when fault_mode = 6 or (fault_mode = 9 and was_stalled = '1') else
                         '1' when fault_mode = 8 and aresetn = '1' else valid or extra;
  process(aclk)
  begin
    if rising_edge(aclk) then
      if aresetn = '0' then
        wa <= 0; wb <= 0; rd <= 0;
        extra <= '0'; toggle <= '0'; was_stalled <= '0';
      else
        toggle <= not toggle;
        was_stalled <= valid and not m_axis_result_tready;
        if s_axis_a_tvalid = '1' and ready_a = '1' then
          qa(wa mod 4) <= s_axis_a_tdata;
          ua(wa mod 4) <= std_logic_vector(resize(unsigned(s_axis_a_tuser), 8));
          la(wa mod 4) <= s_axis_a_tlast;
          wa <= wa + 1;
        end if;
        if s_axis_b_tvalid = '1' and ready_b = '1' and fault_mode /= 13 then
          qb(wb mod 4) <= s_axis_b_tdata;
          ub(wb mod 4) <= std_logic_vector(resize(unsigned(s_axis_b_tuser), 8));
          lb(wb mod 4) <= s_axis_b_tlast;
          wb <= wb + 1;
        end if;
        if valid = '1' and m_axis_result_tready = '1' then
          rd <= rd + 1;
          if fault_mode = 7 and rd = 15 then extra <= '1'; end if;
        elsif extra = '1' and m_axis_result_tready = '1' then
          extra <= '0';
        end if;
      end if;
    end if;
  end process;
  process(all)
    variable value : std_logic_vector(31 downto 0);
    variable users : std_logic_vector(7 downto 0);
    variable ending : std_logic;
    variable flags : std_logic_vector(3 downto 0);
    variable key : std_logic_vector(63 downto 0);
  begin
    key := qa(rd mod 4) & qb(rd mod 4);
    flags := "0000";
    case key is
      when x"3F80000040400000" => value := x"3EAAAAAB";
      when x"3F80000040E00000" => value := x"3E124925";
      when x"3F80000000000000" => value := x"7F800000"; flags := "1000";
      when x"BF80000000000000" | x"3F80000080000000" | x"3F80000080000001" =>
        value := x"FF800000"; flags := "1000";
      when x"0000000000000000" | x"7F8000007F800000" => value := x"7FC00000"; flags := "0100";
      when x"7F80000000000000" => value := x"7F800000";
      when x"00000000BF800000" | x"800000013F800000" | x"3F800000FF800000" => value := x"80000000";
      when x"0080000040000000" => value := x"00000000"; flags := "0001";
      when x"7F7FFFFF3F000000" => value := x"7F800000"; flags := "0010";
      when x"7F80000100000000" => value := x"7FC00000";
      when x"400000003FC00000" => value := x"3FAAAAAB";
      when others => value := (others => 'X');
    end case;
    users := ub(rd mod 4)(4 downto 0) & ua(rd mod 4)(2 downto 0);
    ending := la(rd mod 4) or lb(rd mod 4);
    if fault_mode = 1 then value(0) := not value(0); end if;
    if fault_mode = 2 then users(0) := not users(0); end if;
    if fault_mode = 3 then ending := not ending; end if;
    if fault_mode = 4 then value(0) := 'X'; end if;
    if fault_mode = 5 then value(0) := value(0) xor toggle; end if;
    if fault_mode = 11 then flags(0) := not flags(0); end if;
    if fault_mode = 12 then flags(3) := not flags(3); end if;
    m_axis_result_tdata <= value;
    m_axis_result_tuser <= users & flags;
    m_axis_result_tlast <= ending;
  end process;
end architecture;

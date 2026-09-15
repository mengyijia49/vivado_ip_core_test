library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (
    s_axi_aclk, s_axi_aresetn : in std_logic;
    s_axi_awaddr, s_axi_araddr : in std_logic_vector(4 downto 0);
    s_axi_awvalid, s_axi_wvalid, s_axi_bready, s_axi_arvalid, s_axi_rready : in std_logic;
    s_axi_wdata : in std_logic_vector(31 downto 0);
    s_axi_wstrb : in std_logic_vector(3 downto 0);
    s_axi_awready, s_axi_wready, s_axi_bvalid, s_axi_arready, s_axi_rvalid : out std_logic := '0';
    s_axi_bresp, s_axi_rresp : out std_logic_vector(1 downto 0) := "00";
    s_axi_rdata : out std_logic_vector(31 downto 0) := (others => '0');
    capturetrig0, capturetrig1, freeze : in std_logic;
    generateout0, generateout1, pwm0, interrupt : out std_logic := '0'
  );
end entity;

architecture fixture of dut_0 is
  signal load_value, count : unsigned(7 downto 0) := (others => '0');
  signal control : std_logic_vector(31 downto 0) := (others => '0');
  signal pending_b, pending_r, event_flag, stopped, stretch : std_logic := '0';
begin
  s_axi_awready <= s_axi_aresetn and not pending_b;
  s_axi_wready <= s_axi_aresetn and not pending_b;
  s_axi_arready <= s_axi_aresetn and not pending_r;
  s_axi_bvalid <= pending_b;
  s_axi_rvalid <= pending_r;
  interrupt <= '0' when fault_mode = 4 else event_flag and control(6);
  process(s_axi_aclk)
  begin
    if rising_edge(s_axi_aclk) then
      generateout0 <= '0';
      stretch <= '0';
      if s_axi_aresetn = '0' then
        load_value <= (others => '0'); count <= (others => '0'); control <= (others => '0');
        pending_b <= '0'; pending_r <= '0'; event_flag <= '0'; stopped <= '0';
        s_axi_rdata <= (others => '0');
      else
        if fault_mode = 3 and stretch = '1' then generateout0 <= '1'; end if;
        if pending_b = '1' and s_axi_bready = '1' then pending_b <= '0'; end if;
        if pending_r = '1' and s_axi_rready = '1' then pending_r <= '0'; end if;
        if control(7) = '1' and control(5) = '0' and stopped = '0' and
           (freeze = '0' or fault_mode = 2) then
          if fault_mode = 1 then count <= count+2; else count <= count+1; end if;
          if count = 255 then
            event_flag <= '1'; stopped <= '1';
            if control(2) = '1' and fault_mode /= 5 then
              generateout0 <= '1'; stretch <= '1';
            end if;
          end if;
        end if;
        if s_axi_awvalid = '1' and s_axi_wvalid = '1' and pending_b = '0' then
          pending_b <= '1';
          case to_integer(unsigned(s_axi_awaddr)) is
            when 0 =>
              control <= s_axi_wdata;
              if s_axi_wdata(8) = '1' then event_flag <= '0'; end if;
              if s_axi_wdata(5) = '1' then count <= load_value; stopped <= '0'; end if;
            when 4 => load_value <= unsigned(s_axi_wdata(7 downto 0));
            when others => null;
          end case;
        end if;
        if s_axi_arvalid = '1' and pending_r = '0' then
          pending_r <= '1';
          s_axi_rdata <= (others => '0');
          case to_integer(unsigned(s_axi_araddr)) is
            when 0 => s_axi_rdata <= control; s_axi_rdata(8) <= event_flag;
            when 4 => s_axi_rdata(7 downto 0) <= std_logic_vector(load_value);
            when 8 => s_axi_rdata(7 downto 0) <= std_logic_vector(count);
            when others => null;
          end case;
        end if;
      end if;
    end if;
  end process;
end architecture;

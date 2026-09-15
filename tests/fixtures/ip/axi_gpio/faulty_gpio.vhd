library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (
    s_axi_aclk, s_axi_aresetn : in std_logic;
    s_axi_awaddr, s_axi_araddr : in std_logic_vector(8 downto 0);
    s_axi_awvalid, s_axi_wvalid, s_axi_bready : in std_logic;
    s_axi_arvalid, s_axi_rready : in std_logic;
    s_axi_wdata : in std_logic_vector(31 downto 0);
    s_axi_wstrb : in std_logic_vector(3 downto 0);
    s_axi_awready, s_axi_wready, s_axi_bvalid : out std_logic;
    s_axi_arready, s_axi_rvalid : out std_logic;
    s_axi_bresp, s_axi_rresp : out std_logic_vector(1 downto 0);
    s_axi_rdata : out std_logic_vector(31 downto 0);
    gpio_io_o : out std_logic_vector(7 downto 0);
    ip2intc_irpt : out std_logic
  );
end entity;

architecture fixture of dut_0 is
  signal cycle : natural := 0;
  signal aw_seen, w_seen, bv, rv : std_logic := '0';
  signal stored_address : std_logic_vector(8 downto 0) := (others => '0');
  signal stored_data, rd : std_logic_vector(31 downto 0) := (others => '0');
  signal stored_strobe : std_logic_vector(3 downto 0) := (others => '0');
  signal data_reg : std_logic_vector(7 downto 0) := (others => '0');
  signal gier, ier, isr, b_flip : std_logic := '0';
  signal has_written : boolean := false;
begin
  s_axi_awready <= 'X' when fault_mode = 16 and s_axi_aresetn = '1' else
    '1' when s_axi_aresetn = '1' and aw_seen = '0' and bv = '0' and cycle mod 3 = 0 else '0';
  s_axi_wready <= 'X' when fault_mode = 19 and s_axi_aresetn = '1' else
    '1' when s_axi_aresetn = '1' and w_seen = '0' and bv = '0' and cycle mod 5 = 1 else '0';
  s_axi_arready <= 'X' when fault_mode = 20 and s_axi_aresetn = '1' else
    '1' when s_axi_aresetn = '1' and rv = '0' and cycle mod 4 = 2 else '0';
  s_axi_bvalid <= 'X' when fault_mode = 8 and s_axi_aresetn = '1' else
    '1' when fault_mode = 21 and s_axi_aresetn = '1' and
      (aw_seen = '1' or (s_axi_awvalid = '1' and s_axi_awready = '1')) and
      (w_seen = '1' or (s_axi_wvalid = '1' and s_axi_wready = '1')) else
    '1' when fault_mode = 11 and s_axi_aresetn = '1' else bv;
  s_axi_rvalid <= '1' when fault_mode = 12 and s_axi_aresetn = '1' else
    '1' when fault_mode = 22 and s_axi_arvalid = '1' and s_axi_arready = '1' else rv;
  s_axi_bresp <= "10" when fault_mode = 10 else '0' & b_flip;
  s_axi_rresp <= "10" when fault_mode = 18 else "00";
  s_axi_rdata <= rd(31 downto 1) & 'X' when fault_mode = 9 and rv = '1' else rd;
  gpio_io_o <= data_reg;
  ip2intc_irpt <= '0' when fault_mode = 15 else gier and ier and isr;

  registers : process(s_axi_aclk)
    variable value : std_logic_vector(7 downto 0);
  begin
    if rising_edge(s_axi_aclk) then
      cycle <= cycle+1;
      if s_axi_aresetn = '0' then
        aw_seen <= '0'; w_seen <= '0'; bv <= '0'; rv <= '0'; b_flip <= '0';
        rd <= (others => '0');
        if fault_mode /= 13 or not has_written then
          data_reg <= (others => '0'); gier <= '0'; ier <= '0'; isr <= '0';
        end if;
      else
        if s_axi_awvalid = '1' and s_axi_awready = '1' then
          stored_address <= s_axi_awaddr; aw_seen <= '1';
        end if;
        if s_axi_wvalid = '1' and s_axi_wready = '1' then
          stored_data <= s_axi_wdata; stored_strobe <= s_axi_wstrb; w_seen <= '1';
        end if;
        if aw_seen = '1' and w_seen = '1' then
          aw_seen <= '0'; w_seen <= '0'; has_written <= true;
          if fault_mode /= 2 then bv <= '1'; end if;
          case to_integer(unsigned(stored_address)) is
            when 0 =>
              if fault_mode /= 14 or stored_strobe(0) = '1' then
                value := stored_data(7 downto 0);
                if fault_mode = 1 then value := value xor x"01"; end if;
                data_reg <= value;
              end if;
            when 16#11c# => gier <= stored_data(31);
            when 16#128# => ier <= stored_data(0);
            when 16#120# => isr <= isr xor stored_data(0);
            when others => null;
          end case;
        end if;
        if bv = '1' and s_axi_bready = '1' and fault_mode /= 4 then bv <= '0'; end if;
        if fault_mode = 7 and bv = '1' and s_axi_bready = '0' then b_flip <= not b_flip; end if;
        if s_axi_arvalid = '1' and s_axi_arready = '1' then
          if fault_mode /= 3 then rv <= '1'; end if;
          rd <= (others => '0');
          case to_integer(unsigned(s_axi_araddr)) is
            when 0 => rd(7 downto 0) <= data_reg;
            when 16#11c# => rd(31) <= gier;
            when 16#128# => rd(0) <= ier;
            when 16#120# => rd(0) <= isr;
            when others => null;
          end case;
        end if;
        if rv = '1' and s_axi_rready = '1' and fault_mode /= 5 then rv <= '0'; end if;
        if fault_mode = 6 and rv = '1' and s_axi_rready = '0' then rd <= not rd; end if;
        if fault_mode = 17 and rv = '1' and s_axi_rready = '0' then rv <= '0'; end if;
      end if;
    end if;
  end process;
end architecture;

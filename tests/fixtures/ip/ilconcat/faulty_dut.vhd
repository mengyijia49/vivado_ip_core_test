library ieee;
use ieee.std_logic_1164.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (In0 : in std_logic_vector(0 downto 0);
        In1 : in std_logic_vector(2 downto 0);
        In2 : in std_logic_vector(3 downto 0);
        dout : out std_logic_vector(7 downto 0));
end entity;

architecture fixture of dut_0 is
begin
  correct : if fault_mode = 0 generate dout <= In2 & In1 & In0; end generate;
  reversed_ports : if fault_mode = 1 generate dout <= In0 & In1 & In2; end generate;
  lost_high : if fault_mode = 2 generate dout <= '0' & In2(2 downto 0) & In1 & In0; end generate;
  unknown_bit : if fault_mode = 3 generate dout <= 'X' & In2(2 downto 0) & In1 & In0; end generate;
end architecture;

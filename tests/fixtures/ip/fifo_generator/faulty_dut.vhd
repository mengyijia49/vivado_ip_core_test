library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (clk, srst, wr_en, rd_en : in std_logic;
        din : in std_logic_vector(7 downto 0);
        dout : out std_logic_vector(7 downto 0);
        full, almost_full, wr_ack, overflow, empty, almost_empty, valid, underflow : out std_logic);
end entity;

architecture fixture of dut_0 is
begin
  process
    type samples is array (0 to 7) of std_logic_vector(15 downto 0);
    constant correct : samples := (
      x"A50C", "XXXXXXXX00101101", "XXXXXXXX00101101", x"2502",
      x"2502", x"4A06", "XXXXXXXX00001100", "XXXXXXXX00001101");
    variable value : std_logic_vector(15 downto 0);
  begin
    wait for 200 ns;
    for cycle in 0 to 7 loop
      wait until rising_edge(clk);
      value := correct(cycle);
      if fault_mode = 1 and cycle = 3 then value(8) := not value(8); end if;
      if fault_mode = 2 and cycle = 2 then value(1) := '1'; end if;
      if fault_mode = 3 and cycle = 4 then value(15 downto 8) := x"4A"; end if;
      if fault_mode = 4 and cycle = 3 then value(7) := '1'; end if;
      if fault_mode = 5 and cycle = 3 then value(6) := '1'; end if;
      if fault_mode = 6 and cycle = 1 then value(5) := '0'; end if;
      if fault_mode = 7 and cycle = 3 then value(4) := '1'; end if;
      if fault_mode = 8 and cycle = 3 then value(3) := '1'; end if;
      if fault_mode = 9 and cycle = 5 then value(2) := '0'; end if;
      if fault_mode = 10 and cycle = 7 then value(0) := '0'; end if;
      if fault_mode = 11 and cycle = 3 then value(15) := 'X'; end if;
      dout <= value(15 downto 8);
      full <= value(7); almost_full <= value(6); wr_ack <= value(5); overflow <= value(4);
      empty <= value(3); almost_empty <= value(2); valid <= value(1); underflow <= value(0);
    end loop;
    wait;
  end process;
end architecture;

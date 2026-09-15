library ieee;
use ieee.std_logic_1164.all;

entity dut_0 is
  generic (fault_mode : natural := 0);
  port (clk, srst, wr_en, rd_en : in std_logic;
        din : in std_logic_vector(7 downto 0);
        dout : out std_logic_vector(7 downto 0);
        full, almost_full, wr_ack, overflow, empty, almost_empty, valid, underflow : out std_logic;
        data_count : out std_logic_vector(3 downto 0);
        prog_full, prog_empty : out std_logic);
end entity;

architecture fixture of dut_0 is
begin
  process
    type samples is array (0 to 9) of std_logic_vector(21 downto 0);
    constant correct : samples := (
      "1010010100001100000001",
      "XXXXXXXX00100100000101",
      "XXXXXXXX00100000001001",
      "XXXXXXXX00100000001101",
      "XXXXXXXX00000000001110",
      "0010010100000010001010",
      "0100101000000110000101",
      "0110111100001110000001",
      "XXXXXXXX00001101000001",
      "1010010100001100000001");
    variable value : std_logic_vector(21 downto 0);
  begin
    wait for 200 ns;
    for cycle in 0 to 9 loop
      wait until rising_edge(clk);
      value := correct(cycle);
      if fault_mode = 1 and cycle = 4 then value(2) := not value(2); end if;
      if fault_mode = 2 and cycle = 3 then value(1) := '1'; end if;
      if fault_mode = 3 and cycle = 4 then value(0) := '1'; end if;
      if fault_mode = 4 and cycle = 4 then value(2) := 'X'; end if;
      if fault_mode = 5 and cycle = 1 then value(5 downto 2) := "0000"; end if;
      if fault_mode = 6 and cycle = 9 then value(5 downto 2) := "0011"; end if;
      dout <= value(21 downto 14);
      full <= value(13); almost_full <= value(12); wr_ack <= value(11); overflow <= value(10);
      empty <= value(9); almost_empty <= value(8); valid <= value(7); underflow <= value(6);
      data_count <= value(5 downto 2); prog_full <= value(1); prog_empty <= value(0);
    end loop;
    wait;
  end process;
end architecture;

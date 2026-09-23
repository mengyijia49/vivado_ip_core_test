library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;

entity tb_axi_lmb_selfcheck is
end entity;

architecture test of tb_axi_lmb_selfcheck is
  constant DATA_WIDTH : positive := 32;
  constant ADDR_WIDTH : positive := 32;
  constant ID_WIDTH : positive := 1;
  constant LANES : positive := 4;
  constant ACCESS_COUNT : natural := 137;
  constant OPERATION_COUNT : natural := 143;
  constant FREQUENCY_PROTOCOL : boolean := 0 = 1;
  type natural_array is array(natural range <>) of natural;
  type address_array is array(natural range <>) of std_logic_vector(31 downto 0);
  type data_array is array(natural range <>) of std_logic_vector(31 downto 0);
  type be_array is array(natural range <>) of std_logic_vector(3 downto 0);
  type protection_array is array(natural range <>) of std_logic_vector(1 downto 0);
  constant EXPECTED_ADDR : address_array(0 to 136) := (0 => "00000000000000000000000100000000", 1 => "00000000000000000000000100000000", 2 => "00000000000000000000000111110000", 3 => "00000000000000000000000111110100", 4 => "00000000000000000000000111111000", 5 => "00000000000000000000000111111100", 6 => "00000000000000000000000111110000", 7 => "00000000000000000000000111110100", 8 => "00000000000000000000000111111000", 9 => "00000000000000000000000111111100", 10 => "00000000000000000000001000100000", 11 => "00000000000000000000001000100000", 12 => "00000000000000000000001000100000", 13 => "00000000000000000000001000100000", 14 => "00000000000000000000001000111100", 15 => "00000000000000000000001000110000", 16 => "00000000000000000000001000110100", 17 => "00000000000000000000001000111000", 18 => "00000000000000000000001000111100", 19 => "00000000000000000000001000110000", 20 => "00000000000000000000001000110100", 21 => "00000000000000000000001000111000", 22 => "00000000000000000000001010100000", 23 => "00000000000000000000001010100000", 24 => "00000000000000000000001011000000", 25 => "00000000000000000000001011000000", 26 => "00000000000000000000001011010000", 27 => "00000000000000000000001011010000", 28 => "00000000000000000000000000000000", 29 => "00000000000000000000000000000000", 30 => "01111111111111111111111111111100", 31 => "11111111111111111111111111111100", 32 => "11111111111111111111111111111100", 33 => "00000000000000000000000000000000", 34 => "00000000000000000000000000000000", 35 => "00000000000000000000000000000000", 36 => "00000000000000000000000000000000", 37 => "00000000000000000000000000000000", 38 => "00000000000000000000000000000000", 39 => "00000000000000000000000000000000", 40 => "00000000000000000000000000000000", 41 => "00000000000000000000000000000000", 42 => "00000000000000000000000000000000", 43 => "00000000000000000000000000000000", 44 => "00000000000000000000000000000000", 45 => "00000000000000000000000000000000", 46 => "00000000000000000000000000000000", 47 => "00000000000000000000000000000000", 48 => "00000000000000000000000000000000", 49 => "00000000000000000000000000000000", 50 => "00000000000000000000000000000000", 51 => "00000000000000000000000000000000", 52 => "00000000000000000000000000000000", 53 => "11111111111111111111111111111100", 54 => "11111111111111111111111111111100", 55 => "00000000000000000000000000000000", 56 => "00000000000000000000000000000000", 57 => "00000000000000000000000000000000", 58 => "00000000000000000000000000000000", 59 => "01111111111111111111111111111100", 60 => "01111111111111111111111111111100", 61 => "11111111111111111111111111111100", 62 => "11111111111111111111111111111100", 63 => "11111111111111111111111111111100", 64 => "11111111111111111111111111111100", 65 => "11111111111111111111111111111100", 66 => "11111111111111111111111111111100", 67 => "11111111111111111111111111111100", 68 => "11111111111111111111111111111100", 69 => "11111111111111111111111111111100", 70 => "11111111111111111111111111111100", 71 => "11111111111111111111111111111100", 72 => "11111111111111111111111111111100", 73 => "11111111111111111111111111111100", 74 => "11111111111111111111111111111100", 75 => "11111111111111111111111111111100", 76 => "11111111111111111111111111111100", 77 => "11111111111111111111111111111100", 78 => "11111111111111111111111111111100", 79 => "11111111111111111111111111111100", 80 => "11111111111111111111111111111100", 81 => "11111111111111111111111111111100", 82 => "11111111111111111111111111111100", 83 => "11111111111111111111111111111100", 84 => "11111111111111111111111111111100", 85 => "11111111111111111111111111111100", 86 => "11111111111111111111111111111100", 87 => "11111111111111111111111111111100", 88 => "11111111111111111111111111111100", 89 => "11111111111111111111111111111100", 90 => "11111111111111111111111111111100", 91 => "11111111111111111111111111111100", 92 => "11111111111111111111111111111100", 93 => "11111111111111111111111111111100", 94 => "10010000100111100000111000000100", 95 => "10010000100111100000111000000100", 96 => "11001001111010110000011000111000", 97 => "11001001111010110000011000111000", 98 => "01101001111111101010111100000000", 99 => "01101001111111101010111100000000", 100 => "10101101101110011001111100101000", 101 => "10101101101110011001111100101000", 102 => "11101000000111110011001101111100", 103 => "11101000000111110011001101111100", 104 => "01110100101100110001001100100000", 105 => "01110100101100110001001100100000", 106 => "00110111001101001000101100011100", 107 => "00110111001101001000101100011100", 108 => "11001011101100101001000010001000", 109 => "11001011101100101001000010001000", 110 => "10111110001001111011111100001000", 111 => "10111110001001111011111100001000", 112 => "10011001110011011011111101000000", 113 => "10011001110011011011111101000000", 114 => "01010000100110111111111001011100", 115 => "00110011000110001100011011110000", 116 => "00110011000110001100011011110000", 117 => "11101000111000001001000000011000", 118 => "11101000111000001001000000011000", 119 => "00011001110110011011001000110100", 120 => "00011001110110011011001000110100", 121 => "01011110111000111111000011001000", 122 => "01011110111000111111000011001000", 123 => "11110100111110101110111000110100", 124 => "11110100111110101110111000110100", 125 => "00100011000111100001011011000000", 126 => "00100011000111100001011011000000", 127 => "11000000111010010100001001001100", 128 => "11000000111010010100001001001100", 129 => "11110101011101010001100000011100", 130 => "11110101011101010001100000011100", 131 => "10011111011101011010111001000100", 132 => "10011111011101011010111001000100", 133 => "00010010000100101101000110000000", 134 => "00010010000100101101000110000000", 135 => "11100011001000011010011010111000", 136 => "11100011001000011010011010111000");
  constant EXPECTED_READ : natural_array(0 to 136) := (0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1);
  constant EXPECTED_WRITE : natural_array(0 to 136) := (1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0);
  constant EXPECTED_DATA : data_array(0 to 136) := (0 => "01010000011000000111000010000000", 1 => "00000000000000000000000000000000", 2 => "11111111111111111111111111111111", 3 => "11111111111111111111111011111110", 4 => "11111111111111111111110111111101", 5 => "11111111111111111111110011111100", 6 => "00000000000000000000000000000000", 7 => "00000000000000000000000000000000", 8 => "00000000000000000000000000000000", 9 => "00000000000000000000000000000000", 10 => "01000100001100110010001000010001", 11 => "01000100001100110010001100010000", 12 => "00000000000000000000000000000000", 13 => "00000000000000000000000000000000", 14 => "10100101010110100101101010100101", 15 => "10100101010110100101101110100100", 16 => "10100101010110100101100010100111", 17 => "10100101010110100101100110100110", 18 => "00000000000000000000000000000000", 19 => "00000000000000000000000000000000", 20 => "00000000000000000000000000000000", 21 => "00000000000000000000000000000000", 22 => "00010010001101000101011001111000", 23 => "00000000000000000000000000000000", 24 => "11001010111111101011101010111110", 25 => "00000000000000000000000000000000", 26 => "00010011010101111001101111011111", 27 => "00000000000000000000000000000000", 28 => "00000000000000000000000000000000", 29 => "00000000000000000000000000000000", 30 => "00000000000000000000000000000000", 31 => "00000000000000000000000000000000", 32 => "00000000000000000000000000000000", 33 => "00000000000000000000000000000000", 34 => "00000000000000000000000000000000", 35 => "00000000000000000000000000000000", 36 => "00000000000000000000000000000000", 37 => "00000000000000000000000000000000", 38 => "00000000000000000000000000000000", 39 => "00000000000000000000000000000000", 40 => "00000000000000000000000000000000", 41 => "00000000000000000000000000000000", 42 => "00000000000000000000000000000000", 43 => "00000000000000000000000000000000", 44 => "00000000000000000000000000000000", 45 => "00000000000000000000000000000000", 46 => "00000000000000000000000000000000", 47 => "00000000000000000000000000000000", 48 => "00000000000000000000000000000000", 49 => "00000000000000000000000000000000", 50 => "00000000000000000000000000000000", 51 => "00000000000000000000000000000000", 52 => "00000000000000000000000000000000", 53 => "11111111111111111111111111111111", 54 => "00000000000000000000000000000000", 55 => "11111111111111111111111111111111", 56 => "00000000000000000000000000000000", 57 => "11111111111111111111111111111111", 58 => "00000000000000000000000000000000", 59 => "11111111111111111111111111111111", 60 => "00000000000000000000000000000000", 61 => "11111111111111111111111111111111", 62 => "00000000000000000000000000000000", 63 => "00000000000000000000000000000000", 64 => "00000000000000000000000000000000", 65 => "00000000000000000000000000000001", 66 => "00000000000000000000000000000000", 67 => "01111111111111111111111111111111", 68 => "00000000000000000000000000000000", 69 => "11111111111111111111111111111110", 70 => "00000000000000000000000000000000", 71 => "00000000000000000000000000000000", 72 => "11111111111111111111111111111111", 73 => "00000000000000000000000000000000", 74 => "11111111111111111111111111111111", 75 => "00000000000000000000000000000000", 76 => "11111111111111111111111111111111", 77 => "00000000000000000000000000000000", 78 => "11111111111111111111111111111111", 79 => "00000000000000000000000000000000", 80 => "11111111111111111111111111111111", 81 => "00000000000000000000000000000000", 82 => "11111111111111111111111111111111", 83 => "00000000000000000000000000000000", 84 => "11111111111111111111111111111111", 85 => "00000000000000000000000000000000", 86 => "11111111111111111111111111111111", 87 => "00000000000000000000000000000000", 88 => "11111111111111111111111111111111", 89 => "00000000000000000000000000000000", 90 => "11111111111111111111111111111111", 91 => "00000000000000000000000000000000", 92 => "11111111111111111111111111111111", 93 => "00000000000000000000000000000000", 94 => "00010010110010011111011000111001", 95 => "00000000000000000000000000000000", 96 => "10010100101111000001011101011110", 97 => "00000000000000000000000000000000", 98 => "01000000001010111100100011110111", 99 => "00000000000000000000000000000000", 100 => "01111001011101100000111001101110", 101 => "00000000000000000000000000000000", 102 => "10100011011011100111011101111110", 103 => "00000000000000000000000000000000", 104 => "10100110000001001111000111100000", 105 => "00000000000000000000000000000000", 106 => "00111110111001110100011001100000", 107 => "00000000000000000000000000000000", 108 => "11101000111011111010111110011111", 109 => "00000000000000000000000000000000", 110 => "00100001111001100110011100001000", 111 => "00000000000000000000000000000000", 112 => "11010001001110101110011111111110", 113 => "00000000000000000000000000000000", 114 => "00000000000000000000000000000000", 115 => "01110000010001110011101011100110", 116 => "00000000000000000000000000000000", 117 => "01001000000110000110111001000111", 118 => "00000000000000000000000000000000", 119 => "01011111011110001001100011010110", 120 => "00000000000000000000000000000000", 121 => "00011011010001011010001110101100", 122 => "00000000000000000000000000000000", 123 => "00010000111110000101111100000000", 124 => "00000000000000000000000000000000", 125 => "01101001100001000000100111110010", 126 => "00000000000000000000000000000000", 127 => "01000001001100010100111001000111", 128 => "00000000000000000000000000000000", 129 => "01101001001000110000111000111100", 130 => "00000000000000000000000000000000", 131 => "11001101000011100100011110111000", 132 => "00000000000000000000000000000000", 133 => "00011100011111110001001000011010", 134 => "00000000000000000000000000000000", 135 => "01000110111010101111111000000110", 136 => "00000000000000000000000000000000");
  constant EXPECTED_BE : be_array(0 to 136) := (0 => "1111", 1 => "0000", 2 => "1111", 3 => "1111", 4 => "1111", 5 => "1111", 6 => "0000", 7 => "0000", 8 => "0000", 9 => "0000", 10 => "0011", 11 => "0011", 12 => "0000", 13 => "0000", 14 => "1111", 15 => "1111", 16 => "1111", 17 => "1111", 18 => "0000", 19 => "0000", 20 => "0000", 21 => "0000", 22 => "1111", 23 => "0000", 24 => "1111", 25 => "0000", 26 => "1111", 27 => "0000", 28 => "0000", 29 => "0000", 30 => "0000", 31 => "0000", 32 => "0000", 33 => "0000", 34 => "0000", 35 => "0000", 36 => "0000", 37 => "0001", 38 => "0000", 39 => "0111", 40 => "0000", 41 => "1110", 42 => "0000", 43 => "1111", 44 => "0000", 45 => "0000", 46 => "0000", 47 => "0000", 48 => "0000", 49 => "0000", 50 => "0000", 51 => "0000", 52 => "0000", 53 => "1111", 54 => "0000", 55 => "1111", 56 => "0000", 57 => "1111", 58 => "0000", 59 => "1111", 60 => "0000", 61 => "1111", 62 => "0000", 63 => "1111", 64 => "0000", 65 => "1111", 66 => "0000", 67 => "1111", 68 => "0000", 69 => "1111", 70 => "0000", 71 => "0000", 72 => "0001", 73 => "0000", 74 => "0111", 75 => "0000", 76 => "1110", 77 => "0000", 78 => "1111", 79 => "0000", 80 => "1111", 81 => "0000", 82 => "1111", 83 => "0000", 84 => "1111", 85 => "0000", 86 => "1111", 87 => "0000", 88 => "1111", 89 => "0000", 90 => "1111", 91 => "0000", 92 => "1111", 93 => "0000", 94 => "0010", 95 => "0000", 96 => "1110", 97 => "0000", 98 => "1001", 99 => "0000", 100 => "0010", 101 => "0000", 102 => "0111", 103 => "0000", 104 => "0011", 105 => "0000", 106 => "1001", 107 => "0000", 108 => "0010", 109 => "0000", 110 => "0100", 111 => "0000", 112 => "1111", 113 => "0000", 114 => "0000", 115 => "1000", 116 => "0000", 117 => "0100", 118 => "0000", 119 => "0010", 120 => "0000", 121 => "1011", 122 => "0000", 123 => "0110", 124 => "0000", 125 => "1011", 126 => "0000", 127 => "1100", 128 => "0000", 129 => "0101", 130 => "0000", 131 => "0011", 132 => "0000", 133 => "0100", 134 => "0000", 135 => "1101", 136 => "0000");
  constant EXPECTED_PROT : protection_array(0 to 136) := (0 => "01", 1 => "01", 2 => "10", 3 => "10", 4 => "10", 5 => "10", 6 => "10", 7 => "10", 8 => "10", 9 => "10", 10 => "01", 11 => "01", 12 => "01", 13 => "01", 14 => "01", 15 => "01", 16 => "01", 17 => "01", 18 => "01", 19 => "01", 20 => "01", 21 => "01", 22 => "01", 23 => "01", 24 => "01", 25 => "01", 26 => "01", 27 => "01", 28 => "01", 29 => "01", 30 => "01", 31 => "01", 32 => "01", 33 => "01", 34 => "01", 35 => "01", 36 => "01", 37 => "01", 38 => "01", 39 => "01", 40 => "01", 41 => "01", 42 => "01", 43 => "01", 44 => "01", 45 => "01", 46 => "10", 47 => "10", 48 => "01", 49 => "10", 50 => "01", 51 => "01", 52 => "01", 53 => "10", 54 => "10", 55 => "10", 56 => "10", 57 => "10", 58 => "10", 59 => "10", 60 => "10", 61 => "10", 62 => "10", 63 => "10", 64 => "10", 65 => "10", 66 => "10", 67 => "10", 68 => "10", 69 => "10", 70 => "10", 71 => "10", 72 => "10", 73 => "10", 74 => "10", 75 => "10", 76 => "10", 77 => "10", 78 => "10", 79 => "10", 80 => "01", 81 => "01", 82 => "10", 83 => "10", 84 => "10", 85 => "10", 86 => "01", 87 => "01", 88 => "10", 89 => "10", 90 => "10", 91 => "10", 92 => "10", 93 => "10", 94 => "01", 95 => "01", 96 => "01", 97 => "01", 98 => "01", 99 => "01", 100 => "01", 101 => "01", 102 => "10", 103 => "10", 104 => "01", 105 => "01", 106 => "10", 107 => "10", 108 => "10", 109 => "10", 110 => "10", 111 => "10", 112 => "01", 113 => "01", 114 => "01", 115 => "01", 116 => "01", 117 => "10", 118 => "10", 119 => "01", 120 => "01", 121 => "01", 122 => "01", 123 => "01", 124 => "01", 125 => "10", 126 => "10", 127 => "10", 128 => "10", 129 => "10", 130 => "10", 131 => "10", 132 => "10", 133 => "01", 134 => "01", 135 => "01", 136 => "01");

  signal Clk : std_logic := '0';
  signal Rst : std_logic := '1';

  signal S_AXI_AWID : std_logic_vector(ID_WIDTH-1 downto 0) := (others => '0');
  signal S_AXI_AWADDR : std_logic_vector(ADDR_WIDTH-1 downto 0) := (others => '0');
  signal S_AXI_AWLEN : std_logic_vector(7 downto 0) := (others => '0');
  signal S_AXI_AWSIZE : std_logic_vector(2 downto 0) := (others => '0');
  signal S_AXI_AWBURST : std_logic_vector(1 downto 0) := (others => '0');
  signal S_AXI_AWVALID : std_logic := '0';
  signal S_AXI_AWPROT : std_logic_vector(2 downto 0) := (others => '0');
  signal S_AXI_AWREADY : std_logic;
  signal S_AXI_WDATA : std_logic_vector(DATA_WIDTH-1 downto 0) := (others => '0');
  signal S_AXI_WSTRB : std_logic_vector(LANES-1 downto 0) := (others => '0');
  signal S_AXI_WLAST, S_AXI_WVALID, S_AXI_WREADY : std_logic := '0';
  signal S_AXI_BID : std_logic_vector(ID_WIDTH-1 downto 0);
  signal S_AXI_BRESP : std_logic_vector(1 downto 0);
  signal S_AXI_BVALID : std_logic;
  signal S_AXI_BREADY : std_logic := '0';
  signal S_AXI_ARID : std_logic_vector(ID_WIDTH-1 downto 0) := (others => '0');
  signal S_AXI_ARADDR : std_logic_vector(ADDR_WIDTH-1 downto 0) := (others => '0');
  signal S_AXI_ARLEN : std_logic_vector(7 downto 0) := (others => '0');
  signal S_AXI_ARSIZE : std_logic_vector(2 downto 0) := (others => '0');
  signal S_AXI_ARBURST : std_logic_vector(1 downto 0) := (others => '0');
  signal S_AXI_ARVALID : std_logic := '0';
  signal S_AXI_ARPROT : std_logic_vector(2 downto 0) := (others => '0');
  signal S_AXI_ARREADY : std_logic;
  signal S_AXI_RID : std_logic_vector(ID_WIDTH-1 downto 0);
  signal S_AXI_RDATA : std_logic_vector(DATA_WIDTH-1 downto 0);
  signal S_AXI_RRESP : std_logic_vector(1 downto 0);
  signal S_AXI_RLAST, S_AXI_RVALID : std_logic;
  signal S_AXI_RREADY : std_logic := '0';
  signal M_ABus : std_logic_vector(ADDR_WIDTH-1 downto 0);
  signal M_Prot : std_logic_vector(1 downto 0);
  signal M_ReadStrobe, M_WriteStrobe, M_AddrStrobe : std_logic;
  signal M_DBus : std_logic_vector(DATA_WIDTH-1 downto 0);
  signal M_BE : std_logic_vector(LANES-1 downto 0);
  signal LMB_ReadDBus : std_logic_vector(DATA_WIDTH-1 downto 0) := (others => '0');
  signal LMB_Ready, LMB_UE : std_logic := '0';
  signal LMB_Wait : std_logic := '1';
  signal LMB_CE : std_logic := '0';
  signal read_data_now, read_data_delayed : std_logic_vector(DATA_WIDTH-1 downto 0) := (others => '0');
  signal read_ue_now, read_ue_delayed, write_ue_now : std_logic := '0';
  signal request_is_read : std_logic := '0';
  signal fault_mode : natural range 0 to 2 := 0;
  signal wait_limit : natural range 0 to 3 := 0;
  signal wait_count : natural range 0 to 3 := 0;
  signal access_index : natural range 0 to ACCESS_COUNT := 0;
  signal aw_handshakes, w_handshakes, wlast_handshakes : natural := 0;
  type responder_state_t is (IDLE, WAITING, COMPLETE_GAP);
  signal responder_state : responder_state_t := IDLE;

  function read_value(address : std_logic_vector) return std_logic_vector is
    variable result : std_logic_vector(DATA_WIDTH-1 downto 0) := (others => '0');
    variable base : natural;
  begin
    base := to_integer(unsigned(address(15 downto 0)));
    for lane in 0 to LANES-1 loop
      result(lane*8+7 downto lane*8) := std_logic_vector(to_unsigned((base + lane*49) mod 256, 8));
    end loop;
    return result;
  end function;

  function beat_value(base : std_logic_vector; beat : natural) return std_logic_vector is
    variable result : unsigned(DATA_WIDTH-1 downto 0) := unsigned(base);
  begin
    result := result xor resize(to_unsigned(beat*257, 32), DATA_WIDTH);
    return std_logic_vector(result);
  end function;

  procedure write_bit(variable target : inout line; value : std_logic) is
  begin
    if value = '1' then
      write(target, character'('1'));
    else
      write(target, character'('0'));
    end if;
  end procedure;

  procedure write_bits(variable target : inout line; value : std_logic_vector) is
  begin
    for index in value'range loop
      write_bit(target, value(index));
    end loop;
  end procedure;
begin
  Clk <= not Clk after 5 ns;

  -- Frequency reads return data and UE one cycle after Ready; writes do not.
  LMB_ReadDBus <= read_data_delayed when FREQUENCY_PROTOCOL else read_data_now;
  LMB_UE <= (read_ue_delayed or write_ue_now) when FREQUENCY_PROTOCOL else
            (read_ue_now or write_ue_now);

  dut : entity work.dut_0
    port map (
      Clk => Clk, Rst => Rst,
      S_AXI_AWID => S_AXI_AWID, S_AXI_AWADDR => S_AXI_AWADDR,
      S_AXI_AWLEN => S_AXI_AWLEN, S_AXI_AWSIZE => S_AXI_AWSIZE,
      S_AXI_AWBURST => S_AXI_AWBURST, S_AXI_AWVALID => S_AXI_AWVALID,
      S_AXI_AWPROT => S_AXI_AWPROT, S_AXI_AWREADY => S_AXI_AWREADY,
      S_AXI_WDATA => S_AXI_WDATA, S_AXI_WSTRB => S_AXI_WSTRB,
      S_AXI_WLAST => S_AXI_WLAST, S_AXI_WVALID => S_AXI_WVALID,
      S_AXI_WREADY => S_AXI_WREADY, S_AXI_BID => S_AXI_BID,
      S_AXI_BRESP => S_AXI_BRESP, S_AXI_BVALID => S_AXI_BVALID,
      S_AXI_BREADY => S_AXI_BREADY, S_AXI_ARID => S_AXI_ARID,
      S_AXI_ARADDR => S_AXI_ARADDR, S_AXI_ARLEN => S_AXI_ARLEN,
      S_AXI_ARSIZE => S_AXI_ARSIZE, S_AXI_ARBURST => S_AXI_ARBURST,
      S_AXI_ARVALID => S_AXI_ARVALID, S_AXI_ARPROT => S_AXI_ARPROT,
      S_AXI_ARREADY => S_AXI_ARREADY, S_AXI_RID => S_AXI_RID,
      S_AXI_RDATA => S_AXI_RDATA, S_AXI_RRESP => S_AXI_RRESP,
      S_AXI_RLAST => S_AXI_RLAST, S_AXI_RVALID => S_AXI_RVALID,
      S_AXI_RREADY => S_AXI_RREADY, M_ABus => M_ABus,
      M_ReadStrobe => M_ReadStrobe, M_WriteStrobe => M_WriteStrobe,
      M_AddrStrobe => M_AddrStrobe, M_DBus => M_DBus, M_BE => M_BE,
      LMB_ReadDBus => LMB_ReadDBus, LMB_Ready => LMB_Ready,
      LMB_Wait => LMB_Wait, LMB_UE => LMB_UE, LMB_CE => LMB_CE,
      M_Prot => M_Prot
    );

  lmb_responder : process(Clk)
  begin
    if rising_edge(Clk) then
      LMB_Ready <= '0';
      read_ue_now <= '0';
      write_ue_now <= '0';
      read_data_delayed <= read_data_now;
      read_ue_delayed <= read_ue_now;
      LMB_Wait <= '1';
      if Rst = '1' then
        wait_count <= 0;
        responder_state <= IDLE;
        access_index <= 0;
        read_data_now <= (others => '0');
        read_data_delayed <= (others => '0');
        read_ue_delayed <= '0';
        request_is_read <= '0';
      else
        case responder_state is
          when IDLE =>
            if M_AddrStrobe = '1' then
              assert access_index < ACCESS_COUNT
                report "AXI_LMB_SELF_CHECK_STATUS: FAIL extra LMB access" severity failure;
              assert M_ABus = EXPECTED_ADDR(access_index)
                report "AXI_LMB_SELF_CHECK_STATUS: FAIL LMB address mismatch" severity failure;
              assert M_ReadStrobe = std_logic'val(EXPECTED_READ(access_index)+2) and
                     M_WriteStrobe = std_logic'val(EXPECTED_WRITE(access_index)+2)
                report "AXI_LMB_SELF_CHECK_STATUS: FAIL LMB direction mismatch index=" &
                  integer'image(access_index) & " read=" & std_logic'image(M_ReadStrobe) &
                  " write=" & std_logic'image(M_WriteStrobe) & " expected_read=" &
                  integer'image(EXPECTED_READ(access_index)) & " expected_write=" &
                  integer'image(EXPECTED_WRITE(access_index)) severity failure;
              assert M_DBus = EXPECTED_DATA(access_index) and M_BE = EXPECTED_BE(access_index)
                report "AXI_LMB_SELF_CHECK_STATUS: FAIL LMB write payload mismatch" severity failure;
              access_index <= access_index + 1;
              read_data_now <= read_value(M_ABus);
              request_is_read <= M_ReadStrobe;
              wait_count <= 0;
              responder_state <= WAITING;
            end if;
          when WAITING =>
            if fault_mode = 1 then
              LMB_Wait <= '0';
              responder_state <= COMPLETE_GAP;
            elsif wait_count < wait_limit then
              wait_count <= wait_count + 1;
            else
              LMB_Ready <= '1';
              if fault_mode = 2 then
                read_ue_now <= request_is_read;
                write_ue_now <= not request_is_read;
              end if;
              responder_state <= COMPLETE_GAP;
            end if;
          when COMPLETE_GAP =>
            wait_count <= 0;
            if M_AddrStrobe = '1' then
              assert access_index < ACCESS_COUNT
                report "AXI_LMB_SELF_CHECK_STATUS: FAIL extra LMB access" severity failure;
              assert M_ABus = EXPECTED_ADDR(access_index)
                report "AXI_LMB_SELF_CHECK_STATUS: FAIL LMB address mismatch" severity failure;
              assert M_ReadStrobe = std_logic'val(EXPECTED_READ(access_index)+2) and
                     M_WriteStrobe = std_logic'val(EXPECTED_WRITE(access_index)+2)
                report "AXI_LMB_SELF_CHECK_STATUS: FAIL LMB direction mismatch index=" &
                  integer'image(access_index) & " read=" & std_logic'image(M_ReadStrobe) &
                  " write=" & std_logic'image(M_WriteStrobe) & " expected_read=" &
                  integer'image(EXPECTED_READ(access_index)) & " expected_write=" &
                  integer'image(EXPECTED_WRITE(access_index)) severity failure;
              assert M_DBus = EXPECTED_DATA(access_index) and M_BE = EXPECTED_BE(access_index)
                report "AXI_LMB_SELF_CHECK_STATUS: FAIL LMB write payload mismatch" severity failure;
              access_index <= access_index + 1;
              read_data_now <= read_value(M_ABus);
              request_is_read <= M_ReadStrobe;
              responder_state <= WAITING;
            else
              responder_state <= IDLE;
            end if;
        end case;
      end if;
    end if;
  end process;

  stability_monitor : process(Clk)
    variable b_held, r_held : boolean := false;
    variable held_bid, held_rid : std_logic_vector(ID_WIDTH-1 downto 0);
    variable held_bresp, held_rresp : std_logic_vector(1 downto 0);
    variable held_rdata : std_logic_vector(DATA_WIDTH-1 downto 0);
    variable held_rlast : std_logic;
  begin
    if rising_edge(Clk) then
      if Rst = '1' then
        b_held := false; r_held := false;
        aw_handshakes <= 0; w_handshakes <= 0; wlast_handshakes <= 0;
      else
        if S_AXI_AWVALID = '1' and S_AXI_AWREADY = '1' then
          aw_handshakes <= aw_handshakes + 1;
        end if;
        if S_AXI_WVALID = '1' and S_AXI_WREADY = '1' then
          w_handshakes <= w_handshakes + 1;
          if S_AXI_WLAST = '1' then wlast_handshakes <= wlast_handshakes + 1; end if;
        end if;
        if b_held then
          assert S_AXI_BVALID = '1' and S_AXI_BID = held_bid and S_AXI_BRESP = held_bresp
            report "AXI_LMB_SELF_CHECK_STATUS: FAIL B changed under backpressure" severity failure;
        end if;
        if r_held then
          assert S_AXI_RVALID = '1' and S_AXI_RID = held_rid and
                 S_AXI_RDATA = held_rdata and S_AXI_RRESP = held_rresp and S_AXI_RLAST = held_rlast
            report "AXI_LMB_SELF_CHECK_STATUS: FAIL R changed under backpressure" severity failure;
        end if;
        b_held := S_AXI_BVALID = '1' and S_AXI_BREADY = '0';
        r_held := S_AXI_RVALID = '1' and S_AXI_RREADY = '0';
        if b_held then held_bid := S_AXI_BID; held_bresp := S_AXI_BRESP; end if;
        if r_held then
          held_rid := S_AXI_RID; held_rdata := S_AXI_RDATA;
          held_rresp := S_AXI_RRESP; held_rlast := S_AXI_RLAST;
        end if;
      end if;
    end if;
  end process;

  stimulus : process
    file output_file : text open write_mode is "<REPOSITORY_ROOT>/runs/batches/2026.1/2026-09-23_16-17-52_UTC+0800_46625706/axi_lmb_bridge/axi_lmb_bridge_standard_32/outputs/actual_output.txt";
    variable row : line;

    procedure send_aw(ident : natural; address : std_logic_vector;
                      beats, size, burst, prot : natural) is
    begin
      S_AXI_AWID <= std_logic_vector(to_unsigned(ident, ID_WIDTH));
      S_AXI_AWADDR <= address;
      S_AXI_AWLEN <= std_logic_vector(to_unsigned(beats-1, 8));
      S_AXI_AWSIZE <= std_logic_vector(to_unsigned(size, 3));
      S_AXI_AWBURST <= std_logic_vector(to_unsigned(burst, 2));
      S_AXI_AWPROT <= std_logic_vector(to_unsigned(prot, 3));
      S_AXI_AWVALID <= '1';
      loop wait until rising_edge(Clk); exit when S_AXI_AWREADY = '1'; end loop;
      S_AXI_AWVALID <= '0';
    end procedure;

    procedure send_w(base : std_logic_vector; strobe, beat, beats : natural) is
    begin
      S_AXI_WDATA <= beat_value(base, beat);
      S_AXI_WSTRB <= std_logic_vector(to_unsigned(strobe, LANES));
      if beat = beats-1 then S_AXI_WLAST <= '1'; else S_AXI_WLAST <= '0'; end if;
      S_AXI_WVALID <= '1';
      loop wait until rising_edge(Clk); exit when S_AXI_WREADY = '1'; end loop;
      S_AXI_WVALID <= '0'; S_AXI_WLAST <= '0';
    end procedure;

    procedure drive_write(ident : natural; address : std_logic_vector;
                          beats, size, burst, prot, fault, waits, holds : natural;
                          base : std_logic_vector; strobe : natural; w_first : boolean) is
      variable zero_data : std_logic_vector(DATA_WIDTH-1 downto 0) := (others => '0');
    begin
      fault_mode <= fault; wait_limit <= waits;
      if w_first then
        for beat in 0 to beats-1 loop send_w(base, strobe, beat, beats); end loop;
        send_aw(ident, address, beats, size, burst, prot);
      else
        send_aw(ident, address, beats, size, burst, prot);
        for beat in 0 to beats-1 loop send_w(base, strobe, beat, beats); end loop;
      end if;
      loop wait until rising_edge(Clk); exit when S_AXI_BVALID = '1'; end loop;
      for i in 1 to holds loop wait until rising_edge(Clk); end loop;
      assert not is_x(S_AXI_BID) and not is_x(S_AXI_BRESP)
        report "AXI_LMB_SELF_CHECK_STATUS: FAIL unknown B response" severity failure;
      write_bit(row, '0'); write_bits(row, S_AXI_BID); write_bits(row, zero_data);
      write_bits(row, S_AXI_BRESP); write_bit(row, '0'); writeline(output_file, row);
      S_AXI_BREADY <= '1'; wait until rising_edge(Clk); S_AXI_BREADY <= '0';
    end procedure;

    procedure drive_read(ident : natural; address : std_logic_vector;
                         beats, size, burst, prot, fault, waits, holds : natural) is
    begin
      fault_mode <= fault; wait_limit <= waits;
      S_AXI_ARID <= std_logic_vector(to_unsigned(ident, ID_WIDTH));
      S_AXI_ARADDR <= address;
      S_AXI_ARLEN <= std_logic_vector(to_unsigned(beats-1, 8));
      S_AXI_ARSIZE <= std_logic_vector(to_unsigned(size, 3));
      S_AXI_ARBURST <= std_logic_vector(to_unsigned(burst, 2));
      S_AXI_ARPROT <= std_logic_vector(to_unsigned(prot, 3));
      S_AXI_ARVALID <= '1';
      loop wait until rising_edge(Clk); exit when S_AXI_ARREADY = '1'; end loop;
      S_AXI_ARVALID <= '0';
      for beat in 0 to beats-1 loop
        loop wait until rising_edge(Clk); exit when S_AXI_RVALID = '1'; end loop;
        for i in 1 to holds loop wait until rising_edge(Clk); end loop;
        assert not is_x(S_AXI_RID) and not is_x(S_AXI_RDATA) and
               not is_x(S_AXI_RRESP) and (S_AXI_RLAST = '0' or S_AXI_RLAST = '1')
          report "AXI_LMB_SELF_CHECK_STATUS: FAIL unknown R response" severity failure;
        write_bit(row, '1'); write_bits(row, S_AXI_RID); write_bits(row, S_AXI_RDATA);
        write_bits(row, S_AXI_RRESP); write_bit(row, S_AXI_RLAST); writeline(output_file, row);
        S_AXI_RREADY <= '1'; wait until rising_edge(Clk); S_AXI_RREADY <= '0';
      end loop;
    end procedure;
  begin
    for i in 1 to 6 loop wait until rising_edge(Clk); end loop;
    Rst <= '0';
    for i in 1 to 3 loop wait until rising_edge(Clk); end loop;
    drive_write(1, "00000000000000000000000100000000", 1, 2, 1, 0, 0, 0, 0, "01010000011000000111000010000000", 15, false);
    drive_read(1, "00000000000000000000000100000000", 1, 2, 1, 0, 0, 0, 3);
    drive_write(0, "00000000000000000000000111110000", 4, 2, 1, 1, 0, 2, 0, "11111111111111111111111111111111", 15, false);
    drive_read(0, "00000000000000000000000111110000", 4, 2, 1, 1, 0, 1, 2);
    drive_write(1, "00000000000000000000001000100000", 2, 1, 0, 0, 0, 0, 0, "01000100001100110010001000010001", 3, false);
    drive_read(1, "00000000000000000000001000100000", 2, 1, 0, 0, 0, 0, 0);
    drive_write(0, "00000000000000000000001000111100", 4, 2, 2, 0, 0, 0, 0, "10100101010110100101101010100101", 15, true);
    drive_read(0, "00000000000000000000001000111100", 4, 2, 2, 0, 0, 0, 0);
    drive_write(1, "00000000000000000000001010000000", 1, 2, 1, 0, 0, 0, 0, "11011110101011011011111011101111", 0, false);
    drive_write(0, "00000000000000000000001010100000", 1, 2, 1, 0, 1, 0, 0, "00010010001101000101011001111000", 15, false);
    drive_read(0, "00000000000000000000001010100000", 1, 2, 1, 0, 1, 0, 0);
    drive_write(1, "00000000000000000000001011000000", 1, 2, 1, 0, 2, 0, 0, "11001010111111101011101010111110", 15, false);
    drive_read(1, "00000000000000000000001011000000", 1, 2, 1, 0, 2, 0, 0);
    drive_write(1, "00000000000000000000001011010000", 1, 2, 1, 0, 0, 0, 0, "00010011010101111001101111011111", 15, false);
    drive_read(1, "00000000000000000000001011010000", 1, 2, 1, 0, 0, 0, 0);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 0, "00000000000000000000000000000000", 0, false);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 1);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 1, "00000000000000000000000000000000", 0, true);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 2);
    drive_write(0, "01111111111111111111111111111100", 1, 2, 1, 0, 0, 0, 2, "00000000000000000000000000000000", 0, false);
    drive_read(0, "01111111111111111111111111111100", 1, 2, 1, 0, 0, 1, 3);
    drive_write(0, "11111111111111111111111111111100", 1, 2, 1, 0, 0, 0, 0, "00000000000000000000000000000000", 0, true);
    drive_read(0, "11111111111111111111111111111100", 1, 2, 1, 0, 0, 1, 0);
    drive_write(0, "11111111111111111111111111111100", 1, 2, 1, 0, 0, 0, 1, "00000000000000000000000000000000", 0, false);
    drive_read(0, "11111111111111111111111111111100", 1, 2, 1, 0, 0, 1, 1);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 2, "00000000000000000000000000000001", 0, true);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 2);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 0, "01111111111111111111111111111111", 0, false);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 3);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 1, "11111111111111111111111111111110", 0, true);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 0);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 2, "11111111111111111111111111111111", 0, false);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 1);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 0, "00000000000000000000000000000000", 1, true);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 2);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 1, "00000000000000000000000000000000", 7, false);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 3);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 2, "00000000000000000000000000000000", 14, true);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 0);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 0, "00000000000000000000000000000000", 15, false);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 1);
    drive_write(1, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 1, "00000000000000000000000000000000", 0, true);
    drive_read(1, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 2);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 1, 0, 0, 2, "00000000000000000000000000000000", 0, false);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 1, 0, 1, 3);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 3, 0, 0, 0, "00000000000000000000000000000000", 0, true);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 3, 0, 1, 0);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 6, 0, 0, 1, "00000000000000000000000000000000", 0, false);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 6, 0, 1, 1);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 7, 0, 0, 2, "00000000000000000000000000000000", 0, true);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 7, 0, 1, 2);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 0, "00000000000000000000000000000000", 0, false);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 2, 3);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 2, 1, "00000000000000000000000000000000", 0, true);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 3, 0);
    drive_write(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 3, 2, "00000000000000000000000000000000", 0, false);
    drive_read(0, "00000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 1);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 0, "11111111111111111111111111111111", 15, true);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 2);
    drive_write(1, "00000000000000000000000000000000", 1, 2, 1, 7, 0, 3, 1, "11111111111111111111111111111111", 15, false);
    drive_read(1, "00000000000000000000000000000000", 1, 2, 1, 7, 0, 0, 3);
    drive_write(1, "00000000000000000000000000000000", 1, 2, 1, 7, 0, 3, 2, "11111111111111111111111111111111", 15, true);
    drive_read(1, "00000000000000000000000000000000", 1, 2, 1, 7, 0, 0, 0);
    drive_write(1, "01111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 0, "11111111111111111111111111111111", 15, false);
    drive_read(1, "01111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 1);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 1, "11111111111111111111111111111111", 15, true);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 2);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 2, "00000000000000000000000000000000", 15, false);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 3);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 0, "00000000000000000000000000000001", 15, true);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 0);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 1, "01111111111111111111111111111111", 15, false);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 1);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 2, "11111111111111111111111111111110", 15, true);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 2);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 0, "11111111111111111111111111111111", 0, false);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 3);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 1, "11111111111111111111111111111111", 1, true);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 0);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 2, "11111111111111111111111111111111", 7, false);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 1);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 0, "11111111111111111111111111111111", 14, true);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 2);
    drive_write(0, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 1, "11111111111111111111111111111111", 15, false);
    drive_read(0, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 3);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 0, 0, 3, 2, "11111111111111111111111111111111", 15, true);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 0, 0, 0, 0);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 1, 0, 3, 0, "11111111111111111111111111111111", 15, false);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 1, 0, 0, 1);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 3, 0, 3, 1, "11111111111111111111111111111111", 15, true);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 3, 0, 0, 2);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 6, 0, 3, 2, "11111111111111111111111111111111", 15, false);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 6, 0, 0, 3);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 0, "11111111111111111111111111111111", 15, true);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 1, 0);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 1, 1, "11111111111111111111111111111111", 15, false);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 2, 1);
    drive_write(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 2, 2, "11111111111111111111111111111111", 15, true);
    drive_read(1, "11111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 2);
    drive_write(1, "10010000100111100000111000000100", 1, 2, 1, 0, 0, 1, 0, "00010010110010011111011000111001", 2, false);
    drive_read(1, "10010000100111100000111000000100", 1, 2, 1, 0, 0, 2, 3);
    drive_write(1, "11001001111010110000011000111000", 1, 2, 1, 4, 0, 2, 1, "10010100101111000001011101011110", 14, true);
    drive_read(1, "11001001111010110000011000111000", 1, 2, 1, 4, 0, 3, 0);
    drive_write(1, "01101001111111101010111100000000", 1, 2, 1, 2, 0, 1, 2, "01000000001010111100100011110111", 9, false);
    drive_read(1, "01101001111111101010111100000000", 1, 2, 1, 2, 0, 2, 1);
    drive_write(0, "10101101101110011001111100101000", 1, 2, 1, 2, 0, 0, 0, "01111001011101100000111001101110", 2, true);
    drive_read(0, "10101101101110011001111100101000", 1, 2, 1, 2, 0, 1, 2);
    drive_write(0, "11101000000111110011001101111100", 1, 2, 1, 7, 0, 3, 1, "10100011011011100111011101111110", 7, false);
    drive_read(0, "11101000000111110011001101111100", 1, 2, 1, 7, 0, 0, 3);
    drive_write(1, "01110100101100110001001100100000", 1, 2, 1, 2, 0, 2, 2, "10100110000001001111000111100000", 3, true);
    drive_read(1, "01110100101100110001001100100000", 1, 2, 1, 2, 0, 3, 0);
    drive_write(1, "00110111001101001000101100011100", 1, 2, 1, 7, 0, 1, 0, "00111110111001110100011001100000", 9, false);
    drive_read(1, "00110111001101001000101100011100", 1, 2, 1, 7, 0, 2, 1);
    drive_write(1, "11001011101100101001000010001000", 1, 2, 1, 5, 0, 0, 1, "11101000111011111010111110011111", 2, true);
    drive_read(1, "11001011101100101001000010001000", 1, 2, 1, 5, 0, 1, 2);
    drive_write(1, "10111110001001111011111100001000", 1, 2, 1, 1, 0, 0, 2, "00100001111001100110011100001000", 4, false);
    drive_read(1, "10111110001001111011111100001000", 1, 2, 1, 1, 0, 1, 3);
    drive_write(1, "10011001110011011011111101000000", 1, 2, 1, 2, 0, 0, 0, "11010001001110101110011111111110", 15, true);
    drive_read(1, "10011001110011011011111101000000", 1, 2, 1, 2, 0, 1, 0);
    drive_write(1, "01010000100110111111111001011100", 1, 2, 1, 4, 0, 0, 1, "00010011000101000101110001110110", 0, false);
    drive_read(1, "01010000100110111111111001011100", 1, 2, 1, 4, 0, 1, 1);
    drive_write(1, "00110011000110001100011011110000", 1, 2, 1, 6, 0, 0, 2, "01110000010001110011101011100110", 8, true);
    drive_read(1, "00110011000110001100011011110000", 1, 2, 1, 6, 0, 1, 2);
    drive_write(1, "11101000111000001001000000011000", 1, 2, 1, 5, 0, 2, 0, "01001000000110000110111001000111", 4, false);
    drive_read(1, "11101000111000001001000000011000", 1, 2, 1, 5, 0, 3, 3);
    drive_write(0, "00011001110110011011001000110100", 1, 2, 1, 6, 0, 3, 1, "01011111011110001001100011010110", 2, true);
    drive_read(0, "00011001110110011011001000110100", 1, 2, 1, 6, 0, 0, 0);
    drive_write(0, "01011110111000111111000011001000", 1, 2, 1, 6, 0, 1, 2, "00011011010001011010001110101100", 11, false);
    drive_read(0, "01011110111000111111000011001000", 1, 2, 1, 6, 0, 2, 1);
    drive_write(1, "11110100111110101110111000110100", 1, 2, 1, 2, 0, 3, 0, "00010000111110000101111100000000", 6, true);
    drive_read(1, "11110100111110101110111000110100", 1, 2, 1, 2, 0, 0, 2);
    drive_write(0, "00100011000111100001011011000000", 1, 2, 1, 5, 0, 3, 1, "01101001100001000000100111110010", 11, false);
    drive_read(0, "00100011000111100001011011000000", 1, 2, 1, 5, 0, 0, 3);
    drive_write(0, "11000000111010010100001001001100", 1, 2, 1, 1, 0, 2, 2, "01000001001100010100111001000111", 12, true);
    drive_read(0, "11000000111010010100001001001100", 1, 2, 1, 1, 0, 3, 0);
    drive_write(1, "11110101011101010001100000011100", 1, 2, 1, 1, 0, 3, 0, "01101001001000110000111000111100", 5, false);
    drive_read(1, "11110101011101010001100000011100", 1, 2, 1, 1, 0, 0, 1);
    drive_write(0, "10011111011101011010111001000100", 1, 2, 1, 1, 0, 3, 1, "11001101000011100100011110111000", 3, true);
    drive_read(0, "10011111011101011010111001000100", 1, 2, 1, 1, 0, 0, 2);
    drive_write(0, "00010010000100101101000110000000", 1, 2, 1, 4, 0, 1, 2, "00011100011111110001001000011010", 4, false);
    drive_read(0, "00010010000100101101000110000000", 1, 2, 1, 4, 0, 2, 3);
    drive_write(0, "11100011001000011010011010111000", 1, 2, 1, 2, 0, 1, 0, "01000110111010101111111000000110", 13, true);
    drive_read(0, "11100011001000011010011010111000", 1, 2, 1, 2, 0, 2, 0);
    for i in 1 to 8 loop wait until rising_edge(Clk); end loop;
    assert access_index = ACCESS_COUNT
      report "AXI_LMB_SELF_CHECK_STATUS: FAIL missing LMB access" severity failure;
    report "AXI_LMB_SELF_CHECK_STATUS: PASS" severity failure;
    wait;
  end process;

  timeout : process
  begin
    wait for 148000 ns;
    report "AXI_LMB_SELF_CHECK_STATUS: FAIL timeout access_index=" &
      integer'image(access_index) & " awready=" & std_logic'image(S_AXI_AWREADY) &
      " wready=" & std_logic'image(S_AXI_WREADY) & " bvalid=" & std_logic'image(S_AXI_BVALID) &
      " arready=" & std_logic'image(S_AXI_ARREADY) & " rvalid=" & std_logic'image(S_AXI_RVALID) &
      " addrstrobe=" & std_logic'image(M_AddrStrobe) & " readstrobe=" &
      std_logic'image(M_ReadStrobe) & " writestrobe=" & std_logic'image(M_WriteStrobe) &
      " lmb_ready=" & std_logic'image(LMB_Ready) & " lmb_wait=" & std_logic'image(LMB_Wait)
      & " aw_handshakes=" & integer'image(aw_handshakes)
      & " w_handshakes=" & integer'image(w_handshakes)
      & " wlast_handshakes=" & integer'image(wlast_handshakes)
      severity failure;
  end process;
end architecture;

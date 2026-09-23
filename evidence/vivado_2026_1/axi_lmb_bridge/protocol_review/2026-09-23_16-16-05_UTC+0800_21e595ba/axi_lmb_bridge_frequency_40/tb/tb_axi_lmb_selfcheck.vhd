library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;

entity tb_axi_lmb_selfcheck is
end entity;

architecture test of tb_axi_lmb_selfcheck is
  constant DATA_WIDTH : positive := 32;
  constant ADDR_WIDTH : positive := 40;
  constant ID_WIDTH : positive := 8;
  constant LANES : positive := 4;
  constant ACCESS_COUNT : natural := 133;
  constant OPERATION_COUNT : natural := 143;
  constant FREQUENCY_PROTOCOL : boolean := 1 = 1;
  type natural_array is array(natural range <>) of natural;
  type address_array is array(natural range <>) of std_logic_vector(39 downto 0);
  type data_array is array(natural range <>) of std_logic_vector(31 downto 0);
  type be_array is array(natural range <>) of std_logic_vector(3 downto 0);
  type protection_array is array(natural range <>) of std_logic_vector(1 downto 0);
  constant EXPECTED_ADDR : address_array(0 to 132) := (0 => "0000000000000000000000000000000100000000", 1 => "0000000000000000000000000000000100000000", 2 => "0000000000000000000000000000000111110000", 3 => "0000000000000000000000000000000111110100", 4 => "0000000000000000000000000000000111111000", 5 => "0000000000000000000000000000000111111100", 6 => "0000000000000000000000000000000111110000", 7 => "0000000000000000000000000000000111110100", 8 => "0000000000000000000000000000000111111000", 9 => "0000000000000000000000000000000111111100", 10 => "0000000000000000000000000000001000100000", 11 => "0000000000000000000000000000001000100000", 12 => "0000000000000000000000000000001000100000", 13 => "0000000000000000000000000000001000100000", 14 => "0000000000000000000000000000001000111100", 15 => "0000000000000000000000000000001000110000", 16 => "0000000000000000000000000000001000110100", 17 => "0000000000000000000000000000001000111000", 18 => "0000000000000000000000000000001000111100", 19 => "0000000000000000000000000000001000110000", 20 => "0000000000000000000000000000001000110100", 21 => "0000000000000000000000000000001000111000", 22 => "0000000000000000000000000000001010100000", 23 => "0000000000000000000000000000001010100000", 24 => "0000000000000000000000000000001011000000", 25 => "0000000000000000000000000000001011000000", 26 => "0000000000000000000000000000001011010000", 27 => "0000000000000000000000000000001011010000", 28 => "0000000000000000000000000000000000000000", 29 => "0000000000000000000000000000000000000000", 30 => "0111111111111111111111111111111111111100", 31 => "1111111111111111111111111111111111111100", 32 => "1111111111111111111111111111111111111100", 33 => "0000000000000000000000000000000000000000", 34 => "0000000000000000000000000000000000000000", 35 => "0000000000000000000000000000000000000000", 36 => "0000000000000000000000000000000000000000", 37 => "0000000000000000000000000000000000000000", 38 => "0000000000000000000000000000000000000000", 39 => "0000000000000000000000000000000000000000", 40 => "0000000000000000000000000000000000000000", 41 => "0000000000000000000000000000000000000000", 42 => "0000000000000000000000000000000000000000", 43 => "0000000000000000000000000000000000000000", 44 => "0000000000000000000000000000000000000000", 45 => "0000000000000000000000000000000000000000", 46 => "0000000000000000000000000000000000000000", 47 => "0000000000000000000000000000000000000000", 48 => "0000000000000000000000000000000000000000", 49 => "0000000000000000000000000000000000000000", 50 => "0000000000000000000000000000000000000000", 51 => "0000000000000000000000000000000000000000", 52 => "0000000000000000000000000000000000000000", 53 => "0000000000000000000000000000000000000000", 54 => "0000000000000000000000000000000000000000", 55 => "0000000000000000000000000000000000000000", 56 => "1111111111111111111111111111111111111100", 57 => "1111111111111111111111111111111111111100", 58 => "0000000000000000000000000000000000000000", 59 => "0000000000000000000000000000000000000000", 60 => "0000000000000000000000000000000000000000", 61 => "0000000000000000000000000000000000000000", 62 => "0111111111111111111111111111111111111100", 63 => "0111111111111111111111111111111111111100", 64 => "1111111111111111111111111111111111111100", 65 => "1111111111111111111111111111111111111100", 66 => "1111111111111111111111111111111111111100", 67 => "1111111111111111111111111111111111111100", 68 => "1111111111111111111111111111111111111100", 69 => "1111111111111111111111111111111111111100", 70 => "1111111111111111111111111111111111111100", 71 => "1111111111111111111111111111111111111100", 72 => "1111111111111111111111111111111111111100", 73 => "1111111111111111111111111111111111111100", 74 => "1111111111111111111111111111111111111100", 75 => "1111111111111111111111111111111111111100", 76 => "1111111111111111111111111111111111111100", 77 => "1111111111111111111111111111111111111100", 78 => "1111111111111111111111111111111111111100", 79 => "1111111111111111111111111111111111111100", 80 => "1111111111111111111111111111111111111100", 81 => "1111111111111111111111111111111111111100", 82 => "1111111111111111111111111111111111111100", 83 => "1111111111111111111111111111111111111100", 84 => "1111111111111111111111111111111111111100", 85 => "1111111111111111111111111111111111111100", 86 => "1111111111111111111111111111111111111100", 87 => "1111111111111111111111111111111111111100", 88 => "1111111111111111111111111111111111111100", 89 => "1111111111111111111111111111111111111100", 90 => "1111111111111111111111111111111111111100", 91 => "1111111111111111111111111111111111111100", 92 => "1111111111111111111111111111111111111100", 93 => "1111111111111111111111111111111111111100", 94 => "1111111111111111111111111111111111111100", 95 => "1111111111111111111111111111111111111100", 96 => "1111111111111111111111111111111111111100", 97 => "1111111111111111111111111111111111111100", 98 => "1111111111111111111111111111111111111100", 99 => "1111111111111111111111111111111111111100", 100 => "1111111111111111111111111111111111111100", 101 => "1111111111111111111111111111111111111100", 102 => "1111111111111111111111111111111111111100", 103 => "1000110101001001001111001000011011010100", 104 => "1000110101001001001111001000011011010100", 105 => "0111100100111011111100110110001110001000", 106 => "0111100100111011111100110110001110001000", 107 => "0110111111011111001101101001011100111000", 108 => "0110111111011111001101101001011100111000", 109 => "0001100111001011001110010010100001100100", 110 => "0001100111001011001110010010100001100100", 111 => "0110001111010100110011000111000011011100", 112 => "0110001111010100110011000111000011011100", 113 => "0101011110111001001111111000101001010100", 114 => "0101011110111001001111111000101001010100", 115 => "0011000011101010100101011100010011110000", 116 => "0011000011101010100101011100010011110000", 117 => "1101001110000100101110100000000101100100", 118 => "1101001110000100101110100000000101100100", 119 => "0101010110101100010000101011011000101100", 120 => "0101010110101100010000101011011000101100", 121 => "1011010011110110111111101111011111011000", 122 => "1011010011110110111111101111011111011000", 123 => "0111010011000110011000010101100000011100", 124 => "0111010011000110011000010101100000011100", 125 => "0110001111110001011001000001110010110000", 126 => "0110001111110001011001000001110010110000", 127 => "0110101110001000000110011100010101111100", 128 => "1100111011111000111100010100001111110100", 129 => "1100111011111000111100010100001111110100", 130 => "1110100100011101110101111000100000101100", 131 => "1110100100011101110101111000100000101100", 132 => "1110111001101000111010110100011000101000");
  constant EXPECTED_READ : natural_array(0 to 132) := (0, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1);
  constant EXPECTED_WRITE : natural_array(0 to 132) := (1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 0);
  constant EXPECTED_DATA : data_array(0 to 132) := (0 => "01010000011000000111000010000000", 1 => "00000000000000000000000000000000", 2 => "11111111111111111111111111111111", 3 => "11111111111111111111111011111110", 4 => "11111111111111111111110111111101", 5 => "11111111111111111111110011111100", 6 => "00000000000000000000000000000000", 7 => "00000000000000000000000000000000", 8 => "00000000000000000000000000000000", 9 => "00000000000000000000000000000000", 10 => "01000100001100110010001000010001", 11 => "01000100001100110010001100010000", 12 => "00000000000000000000000000000000", 13 => "00000000000000000000000000000000", 14 => "10100101010110100101101010100101", 15 => "10100101010110100101101110100100", 16 => "10100101010110100101100010100111", 17 => "10100101010110100101100110100110", 18 => "00000000000000000000000000000000", 19 => "00000000000000000000000000000000", 20 => "00000000000000000000000000000000", 21 => "00000000000000000000000000000000", 22 => "00010010001101000101011001111000", 23 => "00000000000000000000000000000000", 24 => "11001010111111101011101010111110", 25 => "00000000000000000000000000000000", 26 => "00010011010101111001101111011111", 27 => "00000000000000000000000000000000", 28 => "00000000000000000000000000000000", 29 => "00000000000000000000000000000000", 30 => "00000000000000000000000000000000", 31 => "00000000000000000000000000000000", 32 => "00000000000000000000000000000000", 33 => "00000000000000000000000000000000", 34 => "00000000000000000000000000000000", 35 => "00000000000000000000000000000000", 36 => "00000000000000000000000000000000", 37 => "00000000000000000000000000000000", 38 => "00000000000000000000000000000000", 39 => "00000000000000000000000000000000", 40 => "00000000000000000000000000000000", 41 => "00000000000000000000000000000000", 42 => "00000000000000000000000000000000", 43 => "00000000000000000000000000000000", 44 => "00000000000000000000000000000000", 45 => "00000000000000000000000000000000", 46 => "00000000000000000000000000000000", 47 => "00000000000000000000000000000000", 48 => "00000000000000000000000000000000", 49 => "00000000000000000000000000000000", 50 => "00000000000000000000000000000000", 51 => "00000000000000000000000000000000", 52 => "00000000000000000000000000000000", 53 => "00000000000000000000000000000000", 54 => "00000000000000000000000000000000", 55 => "00000000000000000000000000000000", 56 => "11111111111111111111111111111111", 57 => "00000000000000000000000000000000", 58 => "11111111111111111111111111111111", 59 => "00000000000000000000000000000000", 60 => "11111111111111111111111111111111", 61 => "00000000000000000000000000000000", 62 => "11111111111111111111111111111111", 63 => "00000000000000000000000000000000", 64 => "11111111111111111111111111111111", 65 => "00000000000000000000000000000000", 66 => "00000000000000000000000000000000", 67 => "00000000000000000000000000000000", 68 => "00000000000000000000000000000001", 69 => "00000000000000000000000000000000", 70 => "01111111111111111111111111111111", 71 => "00000000000000000000000000000000", 72 => "11111111111111111111111111111110", 73 => "00000000000000000000000000000000", 74 => "00000000000000000000000000000000", 75 => "11111111111111111111111111111111", 76 => "00000000000000000000000000000000", 77 => "11111111111111111111111111111111", 78 => "00000000000000000000000000000000", 79 => "11111111111111111111111111111111", 80 => "00000000000000000000000000000000", 81 => "11111111111111111111111111111111", 82 => "00000000000000000000000000000000", 83 => "11111111111111111111111111111111", 84 => "00000000000000000000000000000000", 85 => "11111111111111111111111111111111", 86 => "00000000000000000000000000000000", 87 => "11111111111111111111111111111111", 88 => "00000000000000000000000000000000", 89 => "11111111111111111111111111111111", 90 => "00000000000000000000000000000000", 91 => "11111111111111111111111111111111", 92 => "00000000000000000000000000000000", 93 => "11111111111111111111111111111111", 94 => "00000000000000000000000000000000", 95 => "11111111111111111111111111111111", 96 => "00000000000000000000000000000000", 97 => "11111111111111111111111111111111", 98 => "00000000000000000000000000000000", 99 => "11111111111111111111111111111111", 100 => "00000000000000000000000000000000", 101 => "11111111111111111111111111111111", 102 => "00000000000000000000000000000000", 103 => "00010000010010110001001001000101", 104 => "00000000000000000000000000000000", 105 => "11011011111000101000101001101000", 106 => "00000000000000000000000000000000", 107 => "11101101001001000111101100100101", 108 => "00000000000000000000000000000000", 109 => "00011000000000111011110110000001", 110 => "00000000000000000000000000000000", 111 => "00111110010101000101100111111111", 112 => "00000000000000000000000000000000", 113 => "01000000100010010110111000011100", 114 => "00000000000000000000000000000000", 115 => "10001000000111111011110010110011", 116 => "00000000000000000000000000000000", 117 => "00010110001001001110001101001000", 118 => "00000000000000000000000000000000", 119 => "10100111011001000000001101101111", 120 => "00000000000000000000000000000000", 121 => "10000101110110100000000110111101", 122 => "00000000000000000000000000000000", 123 => "01111001011010111011100001101111", 124 => "00000000000000000000000000000000", 125 => "00011011111001011011001010110010", 126 => "00000000000000000000000000000000", 127 => "00000000000000000000000000000000", 128 => "11011110110100110011100010100000", 129 => "00000000000000000000000000000000", 130 => "10010000010101100111111101101001", 131 => "00000000000000000000000000000000", 132 => "00000000000000000000000000000000");
  constant EXPECTED_BE : be_array(0 to 132) := (0 => "1111", 1 => "0000", 2 => "1111", 3 => "1111", 4 => "1111", 5 => "1111", 6 => "0000", 7 => "0000", 8 => "0000", 9 => "0000", 10 => "0011", 11 => "0011", 12 => "0000", 13 => "0000", 14 => "1111", 15 => "1111", 16 => "1111", 17 => "1111", 18 => "0000", 19 => "0000", 20 => "0000", 21 => "0000", 22 => "1111", 23 => "0000", 24 => "1111", 25 => "0000", 26 => "1111", 27 => "0000", 28 => "0000", 29 => "0000", 30 => "0000", 31 => "0000", 32 => "0000", 33 => "0000", 34 => "0000", 35 => "0000", 36 => "0000", 37 => "0001", 38 => "0000", 39 => "0111", 40 => "0000", 41 => "1110", 42 => "0000", 43 => "1111", 44 => "0000", 45 => "0000", 46 => "0000", 47 => "0000", 48 => "0000", 49 => "0000", 50 => "0000", 51 => "0000", 52 => "0000", 53 => "0000", 54 => "0000", 55 => "0000", 56 => "1111", 57 => "0000", 58 => "1111", 59 => "0000", 60 => "1111", 61 => "0000", 62 => "1111", 63 => "0000", 64 => "1111", 65 => "0000", 66 => "1111", 67 => "0000", 68 => "1111", 69 => "0000", 70 => "1111", 71 => "0000", 72 => "1111", 73 => "0000", 74 => "0000", 75 => "0001", 76 => "0000", 77 => "0111", 78 => "0000", 79 => "1110", 80 => "0000", 81 => "1111", 82 => "0000", 83 => "1111", 84 => "0000", 85 => "1111", 86 => "0000", 87 => "1111", 88 => "0000", 89 => "1111", 90 => "0000", 91 => "1111", 92 => "0000", 93 => "1111", 94 => "0000", 95 => "1111", 96 => "0000", 97 => "1111", 98 => "0000", 99 => "1111", 100 => "0000", 101 => "1111", 102 => "0000", 103 => "0100", 104 => "0000", 105 => "0110", 106 => "0000", 107 => "0011", 108 => "0000", 109 => "0010", 110 => "0000", 111 => "1010", 112 => "0000", 113 => "0101", 114 => "0000", 115 => "1011", 116 => "0000", 117 => "1000", 118 => "0000", 119 => "1101", 120 => "0000", 121 => "1100", 122 => "0000", 123 => "1001", 124 => "0000", 125 => "0110", 126 => "0000", 127 => "0000", 128 => "0111", 129 => "0000", 130 => "0001", 131 => "0000", 132 => "0000");
  constant EXPECTED_PROT : protection_array(0 to 132) := (0 => "01", 1 => "01", 2 => "10", 3 => "10", 4 => "10", 5 => "10", 6 => "10", 7 => "10", 8 => "10", 9 => "10", 10 => "01", 11 => "01", 12 => "01", 13 => "01", 14 => "01", 15 => "01", 16 => "01", 17 => "01", 18 => "01", 19 => "01", 20 => "01", 21 => "01", 22 => "01", 23 => "01", 24 => "01", 25 => "01", 26 => "01", 27 => "01", 28 => "01", 29 => "01", 30 => "01", 31 => "01", 32 => "01", 33 => "01", 34 => "01", 35 => "01", 36 => "01", 37 => "01", 38 => "01", 39 => "01", 40 => "01", 41 => "01", 42 => "01", 43 => "01", 44 => "01", 45 => "01", 46 => "01", 47 => "01", 48 => "01", 49 => "10", 50 => "10", 51 => "01", 52 => "10", 53 => "01", 54 => "01", 55 => "01", 56 => "10", 57 => "10", 58 => "10", 59 => "10", 60 => "10", 61 => "10", 62 => "10", 63 => "10", 64 => "10", 65 => "10", 66 => "10", 67 => "10", 68 => "10", 69 => "10", 70 => "10", 71 => "10", 72 => "10", 73 => "10", 74 => "10", 75 => "10", 76 => "10", 77 => "10", 78 => "10", 79 => "10", 80 => "10", 81 => "10", 82 => "10", 83 => "10", 84 => "10", 85 => "10", 86 => "10", 87 => "10", 88 => "10", 89 => "01", 90 => "01", 91 => "10", 92 => "10", 93 => "10", 94 => "10", 95 => "01", 96 => "01", 97 => "10", 98 => "10", 99 => "10", 100 => "10", 101 => "10", 102 => "10", 103 => "01", 104 => "01", 105 => "10", 106 => "10", 107 => "01", 108 => "01", 109 => "01", 110 => "01", 111 => "10", 112 => "10", 113 => "10", 114 => "10", 115 => "10", 116 => "10", 117 => "10", 118 => "10", 119 => "01", 120 => "01", 121 => "10", 122 => "10", 123 => "01", 124 => "01", 125 => "10", 126 => "10", 127 => "01", 128 => "10", 129 => "10", 130 => "10", 131 => "10", 132 => "01");

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
      LMB_UE <= '0';
      LMB_Wait <= '1';
      if Rst = '1' then
        wait_count <= 0;
        responder_state <= IDLE;
        access_index <= 0;
        LMB_ReadDBus <= (others => '0');
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
        assert M_Prot = EXPECTED_PROT(access_index)
          report "AXI_LMB_SELF_CHECK_STATUS: FAIL LMB protection mismatch index=" &
            integer'image(access_index) & " actual=" & integer'image(to_integer(unsigned(M_Prot))) &
            " expected=" & integer'image(to_integer(unsigned(EXPECTED_PROT(access_index))))
            severity failure;
              access_index <= access_index + 1;
              LMB_ReadDBus <= read_value(M_ABus);
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
              if fault_mode = 2 then LMB_UE <= '1'; end if;
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
        assert M_Prot = EXPECTED_PROT(access_index)
          report "AXI_LMB_SELF_CHECK_STATUS: FAIL LMB protection mismatch index=" &
            integer'image(access_index) & " actual=" & integer'image(to_integer(unsigned(M_Prot))) &
            " expected=" & integer'image(to_integer(unsigned(EXPECTED_PROT(access_index))))
            severity failure;
              access_index <= access_index + 1;
              LMB_ReadDBus <= read_value(M_ABus);
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
    file output_file : text open write_mode is "<REPOSITORY_ROOT>/runs/batches/2026.1/2026-09-23_16-16-05_UTC+0800_21e595ba/axi_lmb_bridge/axi_lmb_bridge_frequency_40/outputs/actual_output.txt";
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
    drive_write(1, "0000000000000000000000000000000100000000", 1, 2, 1, 0, 0, 0, 0, "01010000011000000111000010000000", 15, false);
    drive_read(1, "0000000000000000000000000000000100000000", 1, 2, 1, 0, 0, 0, 3);
    drive_write(2, "0000000000000000000000000000000111110000", 4, 2, 1, 1, 0, 2, 0, "11111111111111111111111111111111", 15, false);
    drive_read(2, "0000000000000000000000000000000111110000", 4, 2, 1, 1, 0, 1, 2);
    drive_write(3, "0000000000000000000000000000001000100000", 2, 1, 0, 0, 0, 0, 0, "01000100001100110010001000010001", 3, false);
    drive_read(3, "0000000000000000000000000000001000100000", 2, 1, 0, 0, 0, 0, 0);
    drive_write(4, "0000000000000000000000000000001000111100", 4, 2, 2, 0, 0, 0, 0, "10100101010110100101101010100101", 15, true);
    drive_read(4, "0000000000000000000000000000001000111100", 4, 2, 2, 0, 0, 0, 0);
    drive_write(5, "0000000000000000000000000000001010000000", 1, 2, 1, 0, 0, 0, 0, "11011110101011011011111011101111", 0, false);
    drive_write(6, "0000000000000000000000000000001010100000", 1, 2, 1, 0, 1, 0, 0, "00010010001101000101011001111000", 15, false);
    drive_read(6, "0000000000000000000000000000001010100000", 1, 2, 1, 0, 1, 0, 0);
    drive_write(7, "0000000000000000000000000000001011000000", 1, 2, 1, 0, 2, 0, 0, "11001010111111101011101010111110", 15, false);
    drive_read(7, "0000000000000000000000000000001011000000", 1, 2, 1, 0, 2, 0, 0);
    drive_write(1, "0000000000000000000000000000001011010000", 1, 2, 1, 0, 0, 0, 0, "00010011010101111001101111011111", 15, false);
    drive_read(1, "0000000000000000000000000000001011010000", 1, 2, 1, 0, 0, 0, 0);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 0, "00000000000000000000000000000000", 0, false);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 1);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 1, "00000000000000000000000000000000", 0, true);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 2);
    drive_write(0, "0111111111111111111111111111111111111100", 1, 2, 1, 0, 0, 0, 2, "00000000000000000000000000000000", 0, false);
    drive_read(0, "0111111111111111111111111111111111111100", 1, 2, 1, 0, 0, 1, 3);
    drive_write(0, "1111111111111111111111111111111111111100", 1, 2, 1, 0, 0, 0, 0, "00000000000000000000000000000000", 0, true);
    drive_read(0, "1111111111111111111111111111111111111100", 1, 2, 1, 0, 0, 1, 0);
    drive_write(0, "1111111111111111111111111111111111111100", 1, 2, 1, 0, 0, 0, 1, "00000000000000000000000000000000", 0, false);
    drive_read(0, "1111111111111111111111111111111111111100", 1, 2, 1, 0, 0, 1, 1);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 2, "00000000000000000000000000000001", 0, true);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 2);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 0, "01111111111111111111111111111111", 0, false);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 3);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 1, "11111111111111111111111111111110", 0, true);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 0);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 2, "11111111111111111111111111111111", 0, false);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 1);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 0, "00000000000000000000000000000000", 1, true);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 2);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 1, "00000000000000000000000000000000", 7, false);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 3);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 2, "00000000000000000000000000000000", 14, true);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 0);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 0, "00000000000000000000000000000000", 15, false);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 1);
    drive_write(1, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 1, "00000000000000000000000000000000", 0, true);
    drive_read(1, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 2);
    drive_write(127, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 2, "00000000000000000000000000000000", 0, false);
    drive_read(127, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 3);
    drive_write(254, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 0, "00000000000000000000000000000000", 0, true);
    drive_read(254, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 0);
    drive_write(255, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 1, "00000000000000000000000000000000", 0, false);
    drive_read(255, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 1);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 1, 0, 0, 2, "00000000000000000000000000000000", 0, true);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 1, 0, 1, 2);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 3, 0, 0, 0, "00000000000000000000000000000000", 0, false);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 3, 0, 1, 3);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 6, 0, 0, 1, "00000000000000000000000000000000", 0, true);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 6, 0, 1, 0);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 7, 0, 0, 2, "00000000000000000000000000000000", 0, false);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 7, 0, 1, 1);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 1, 0, "00000000000000000000000000000000", 0, true);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 2, 2);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 2, 1, "00000000000000000000000000000000", 0, false);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 3, 3);
    drive_write(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 3, 2, "00000000000000000000000000000000", 0, true);
    drive_read(0, "0000000000000000000000000000000000000000", 1, 2, 1, 0, 0, 0, 0);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 0, "11111111111111111111111111111111", 15, false);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 1);
    drive_write(255, "0000000000000000000000000000000000000000", 1, 2, 1, 7, 0, 3, 1, "11111111111111111111111111111111", 15, true);
    drive_read(255, "0000000000000000000000000000000000000000", 1, 2, 1, 7, 0, 0, 2);
    drive_write(255, "0000000000000000000000000000000000000000", 1, 2, 1, 7, 0, 3, 2, "11111111111111111111111111111111", 15, false);
    drive_read(255, "0000000000000000000000000000000000000000", 1, 2, 1, 7, 0, 0, 3);
    drive_write(255, "0111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 0, "11111111111111111111111111111111", 15, true);
    drive_read(255, "0111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 0);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 1, "11111111111111111111111111111111", 15, false);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 1);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 2, "00000000000000000000000000000000", 15, true);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 2);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 0, "00000000000000000000000000000001", 15, false);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 3);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 1, "01111111111111111111111111111111", 15, true);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 0);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 2, "11111111111111111111111111111110", 15, false);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 1);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 0, "11111111111111111111111111111111", 0, true);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 2);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 1, "11111111111111111111111111111111", 1, false);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 3);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 2, "11111111111111111111111111111111", 7, true);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 0);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 0, "11111111111111111111111111111111", 14, false);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 1);
    drive_write(0, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 1, "11111111111111111111111111111111", 15, true);
    drive_read(0, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 2);
    drive_write(1, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 2, "11111111111111111111111111111111", 15, false);
    drive_read(1, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 3);
    drive_write(127, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 0, "11111111111111111111111111111111", 15, true);
    drive_read(127, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 0);
    drive_write(254, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 1, "11111111111111111111111111111111", 15, false);
    drive_read(254, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 1);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 0, 0, 3, 2, "11111111111111111111111111111111", 15, true);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 0, 0, 0, 2);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 1, 0, 3, 0, "11111111111111111111111111111111", 15, false);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 1, 0, 0, 3);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 3, 0, 3, 1, "11111111111111111111111111111111", 15, true);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 3, 0, 0, 0);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 6, 0, 3, 2, "11111111111111111111111111111111", 15, false);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 6, 0, 0, 1);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 0, 0, "11111111111111111111111111111111", 15, true);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 1, 2);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 1, 1, "11111111111111111111111111111111", 15, false);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 2, 3);
    drive_write(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 2, 2, "11111111111111111111111111111111", 15, true);
    drive_read(255, "1111111111111111111111111111111111111100", 1, 2, 1, 7, 0, 3, 0);
    drive_write(148, "1000110101001001001111001000011011010100", 1, 2, 1, 2, 0, 1, 0, "00010000010010110001001001000101", 4, false);
    drive_read(148, "1000110101001001001111001000011011010100", 1, 2, 1, 2, 0, 2, 1);
    drive_write(96, "0111100100111011111100110110001110001000", 1, 2, 1, 5, 0, 1, 1, "11011011111000101000101001101000", 6, true);
    drive_read(96, "0111100100111011111100110110001110001000", 1, 2, 1, 5, 0, 2, 2);
    drive_write(109, "0110111111011111001101101001011100111000", 1, 2, 1, 4, 0, 1, 2, "11101101001001000111101100100101", 3, false);
    drive_read(109, "0110111111011111001101101001011100111000", 1, 2, 1, 4, 0, 2, 3);
    drive_write(195, "0001100111001011001110010010100001100100", 1, 2, 1, 0, 0, 3, 0, "00011000000000111011110110000001", 2, true);
    drive_read(195, "0001100111001011001110010010100001100100", 1, 2, 1, 0, 0, 0, 0);
    drive_write(76, "0110001111010100110011000111000011011100", 1, 2, 1, 1, 0, 3, 1, "00111110010101000101100111111111", 10, false);
    drive_read(76, "0110001111010100110011000111000011011100", 1, 2, 1, 1, 0, 0, 1);
    drive_write(74, "0101011110111001001111111000101001010100", 1, 2, 1, 5, 0, 1, 2, "01000000100010010110111000011100", 5, true);
    drive_read(74, "0101011110111001001111111000101001010100", 1, 2, 1, 5, 0, 2, 2);
    drive_write(229, "0011000011101010100101011100010011110000", 1, 2, 1, 5, 0, 2, 0, "10001000000111111011110010110011", 11, false);
    drive_read(229, "0011000011101010100101011100010011110000", 1, 2, 1, 5, 0, 3, 3);
    drive_write(18, "1101001110000100101110100000000101100100", 1, 2, 1, 1, 0, 3, 1, "00010110001001001110001101001000", 8, true);
    drive_read(18, "1101001110000100101110100000000101100100", 1, 2, 1, 1, 0, 0, 0);
    drive_write(9, "0101010110101100010000101011011000101100", 1, 2, 1, 6, 0, 2, 2, "10100111011001000000001101101111", 13, false);
    drive_read(9, "0101010110101100010000101011011000101100", 1, 2, 1, 6, 0, 3, 1);
    drive_write(178, "1011010011110110111111101111011111011000", 1, 2, 1, 3, 0, 0, 0, "10000101110110100000000110111101", 12, true);
    drive_read(178, "1011010011110110111111101111011111011000", 1, 2, 1, 3, 0, 1, 2);
    drive_write(53, "0111010011000110011000010101100000011100", 1, 2, 1, 4, 0, 1, 1, "01111001011010111011100001101111", 9, false);
    drive_read(53, "0111010011000110011000010101100000011100", 1, 2, 1, 4, 0, 2, 3);
    drive_write(58, "0110001111110001011001000001110010110000", 1, 2, 1, 3, 0, 0, 2, "00011011111001011011001010110010", 6, true);
    drive_read(58, "0110001111110001011001000001110010110000", 1, 2, 1, 3, 0, 1, 0);
    drive_write(213, "0110101110001000000110011100010101111100", 1, 2, 1, 0, 0, 3, 0, "01100011001100010100001000011001", 0, false);
    drive_read(213, "0110101110001000000110011100010101111100", 1, 2, 1, 0, 0, 0, 1);
    drive_write(215, "1100111011111000111100010100001111110100", 1, 2, 1, 5, 0, 3, 1, "11011110110100110011100010100000", 7, true);
    drive_read(215, "1100111011111000111100010100001111110100", 1, 2, 1, 5, 0, 0, 2);
    drive_write(185, "1110100100011101110101111000100000101100", 1, 2, 1, 7, 0, 2, 2, "10010000010101100111111101101001", 1, false);
    drive_read(185, "1110100100011101110101111000100000101100", 1, 2, 1, 7, 0, 3, 3);
    drive_write(4, "1110111001101000111010110100011000101000", 1, 2, 1, 4, 0, 2, 0, "01101000000111000011110110001000", 0, true);
    drive_read(4, "1110111001101000111010110100011000101000", 1, 2, 1, 4, 0, 3, 0);
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

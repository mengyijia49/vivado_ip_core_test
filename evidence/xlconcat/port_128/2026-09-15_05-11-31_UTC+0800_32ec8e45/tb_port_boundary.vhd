library ieee;
use ieee.std_logic_1164.all;
use std.env.all;

entity tb_port_boundary is
end entity;

architecture sim of tb_port_boundary is
  signal stimulus, actual : std_logic_vector(127 downto 0) := (others => '0');
begin
  dut : entity work.dut_0
    port map (
      In0 => stimulus(0 downto 0),
      In1 => stimulus(1 downto 1),
      In2 => stimulus(2 downto 2),
      In3 => stimulus(3 downto 3),
      In4 => stimulus(4 downto 4),
      In5 => stimulus(5 downto 5),
      In6 => stimulus(6 downto 6),
      In7 => stimulus(7 downto 7),
      In8 => stimulus(8 downto 8),
      In9 => stimulus(9 downto 9),
      In10 => stimulus(10 downto 10),
      In11 => stimulus(11 downto 11),
      In12 => stimulus(12 downto 12),
      In13 => stimulus(13 downto 13),
      In14 => stimulus(14 downto 14),
      In15 => stimulus(15 downto 15),
      In16 => stimulus(16 downto 16),
      In17 => stimulus(17 downto 17),
      In18 => stimulus(18 downto 18),
      In19 => stimulus(19 downto 19),
      In20 => stimulus(20 downto 20),
      In21 => stimulus(21 downto 21),
      In22 => stimulus(22 downto 22),
      In23 => stimulus(23 downto 23),
      In24 => stimulus(24 downto 24),
      In25 => stimulus(25 downto 25),
      In26 => stimulus(26 downto 26),
      In27 => stimulus(27 downto 27),
      In28 => stimulus(28 downto 28),
      In29 => stimulus(29 downto 29),
      In30 => stimulus(30 downto 30),
      In31 => stimulus(31 downto 31),
      In32 => stimulus(32 downto 32),
      In33 => stimulus(33 downto 33),
      In34 => stimulus(34 downto 34),
      In35 => stimulus(35 downto 35),
      In36 => stimulus(36 downto 36),
      In37 => stimulus(37 downto 37),
      In38 => stimulus(38 downto 38),
      In39 => stimulus(39 downto 39),
      In40 => stimulus(40 downto 40),
      In41 => stimulus(41 downto 41),
      In42 => stimulus(42 downto 42),
      In43 => stimulus(43 downto 43),
      In44 => stimulus(44 downto 44),
      In45 => stimulus(45 downto 45),
      In46 => stimulus(46 downto 46),
      In47 => stimulus(47 downto 47),
      In48 => stimulus(48 downto 48),
      In49 => stimulus(49 downto 49),
      In50 => stimulus(50 downto 50),
      In51 => stimulus(51 downto 51),
      In52 => stimulus(52 downto 52),
      In53 => stimulus(53 downto 53),
      In54 => stimulus(54 downto 54),
      In55 => stimulus(55 downto 55),
      In56 => stimulus(56 downto 56),
      In57 => stimulus(57 downto 57),
      In58 => stimulus(58 downto 58),
      In59 => stimulus(59 downto 59),
      In60 => stimulus(60 downto 60),
      In61 => stimulus(61 downto 61),
      In62 => stimulus(62 downto 62),
      In63 => stimulus(63 downto 63),
      In64 => stimulus(64 downto 64),
      In65 => stimulus(65 downto 65),
      In66 => stimulus(66 downto 66),
      In67 => stimulus(67 downto 67),
      In68 => stimulus(68 downto 68),
      In69 => stimulus(69 downto 69),
      In70 => stimulus(70 downto 70),
      In71 => stimulus(71 downto 71),
      In72 => stimulus(72 downto 72),
      In73 => stimulus(73 downto 73),
      In74 => stimulus(74 downto 74),
      In75 => stimulus(75 downto 75),
      In76 => stimulus(76 downto 76),
      In77 => stimulus(77 downto 77),
      In78 => stimulus(78 downto 78),
      In79 => stimulus(79 downto 79),
      In80 => stimulus(80 downto 80),
      In81 => stimulus(81 downto 81),
      In82 => stimulus(82 downto 82),
      In83 => stimulus(83 downto 83),
      In84 => stimulus(84 downto 84),
      In85 => stimulus(85 downto 85),
      In86 => stimulus(86 downto 86),
      In87 => stimulus(87 downto 87),
      In88 => stimulus(88 downto 88),
      In89 => stimulus(89 downto 89),
      In90 => stimulus(90 downto 90),
      In91 => stimulus(91 downto 91),
      In92 => stimulus(92 downto 92),
      In93 => stimulus(93 downto 93),
      In94 => stimulus(94 downto 94),
      In95 => stimulus(95 downto 95),
      In96 => stimulus(96 downto 96),
      In97 => stimulus(97 downto 97),
      In98 => stimulus(98 downto 98),
      In99 => stimulus(99 downto 99),
      In100 => stimulus(100 downto 100),
      In101 => stimulus(101 downto 101),
      In102 => stimulus(102 downto 102),
      In103 => stimulus(103 downto 103),
      In104 => stimulus(104 downto 104),
      In105 => stimulus(105 downto 105),
      In106 => stimulus(106 downto 106),
      In107 => stimulus(107 downto 107),
      In108 => stimulus(108 downto 108),
      In109 => stimulus(109 downto 109),
      In110 => stimulus(110 downto 110),
      In111 => stimulus(111 downto 111),
      In112 => stimulus(112 downto 112),
      In113 => stimulus(113 downto 113),
      In114 => stimulus(114 downto 114),
      In115 => stimulus(115 downto 115),
      In116 => stimulus(116 downto 116),
      In117 => stimulus(117 downto 117),
      In118 => stimulus(118 downto 118),
      In119 => stimulus(119 downto 119),
      In120 => stimulus(120 downto 120),
      In121 => stimulus(121 downto 121),
      In122 => stimulus(122 downto 122),
      In123 => stimulus(123 downto 123),
      In124 => stimulus(124 downto 124),
      In125 => stimulus(125 downto 125),
      In126 => stimulus(126 downto 126),
      In127 => stimulus(127 downto 127),
      dout => actual
    );

  exercise : process
    variable word : std_logic_vector(stimulus'range);
    variable mismatches : natural := 0;
    procedure observe(name : string; expected : std_logic_vector) is
    begin
      report "CONCAT_PORT_OBSERVATION " & name & " expected=" & to_string(expected) &
             " actual=" & to_string(actual);
      if is_x(actual) or actual /= expected then
        mismatches := mismatches + 1;
      end if;
    end procedure;
  begin
    wait for 1 us;
    word := (others => '0');
    observe("zero", word);
    word := (others => '1');
    stimulus <= word;
    wait for 1 us;
    observe("ones", word);
    wait for 5 us;
    observe("ones_late", word);
    word := (word'high => '1', others => '0');
    stimulus <= word;
    wait for 1 us;
    observe("high", word);
    word := (0 => '1', others => '0');
    stimulus <= word;
    wait for 1 us;
    observe("low", word);
    for bit in word'range loop
      if bit mod 2 = 0 then word(bit) := '1'; else word(bit) := '0'; end if;
    end loop;
    stimulus <= word;
    wait for 1 us;
    observe("alternating", word);
    report "CONCAT_PORT_MISMATCHES " & integer'image(mismatches);
    report "CONCAT_PORT_PROBE: COMPLETE";
    finish;
    wait;
  end process;
end architecture;

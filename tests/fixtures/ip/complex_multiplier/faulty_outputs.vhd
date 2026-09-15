library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity dut_0 is
  port (s_axis_a_tdata, s_axis_b_tdata : in std_logic_vector(15 downto 0);
        s_axis_a_tvalid, s_axis_b_tvalid : in std_logic;
        m_axis_dout_tvalid : out std_logic;
        m_axis_dout_tdata : out std_logic_vector(47 downto 0));
end entity;

architecture fault_fixture of dut_0 is
begin
  process (s_axis_a_tdata, s_axis_b_tdata, s_axis_a_tvalid, s_axis_b_tvalid)
    variable ar, ai, br, bi, real_part, imaginary_part : integer;
    variable data : std_logic_vector(47 downto 0);
  begin
    ar := to_integer(signed(s_axis_a_tdata(7 downto 0)));
    ai := to_integer(signed(s_axis_a_tdata(15 downto 8)));
    br := to_integer(signed(s_axis_b_tdata(7 downto 0)));
    bi := to_integer(signed(s_axis_b_tdata(15 downto 8)));
    real_part := ar * br - ai * bi;
    imaginary_part := ar * bi + ai * br;
    data := std_logic_vector(to_signed(imaginary_part, 24)) & std_logic_vector(to_signed(real_part, 24));
    if ar = -1 then
      data(23 downto 17) := (others => '0');
    end if;
    m_axis_dout_tdata <= data;
    m_axis_dout_tvalid <= s_axis_a_tvalid or s_axis_b_tvalid;
  end process;
end architecture;

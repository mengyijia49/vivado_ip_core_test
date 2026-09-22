def apb_harness(parameters):
    slaves = parameters["num_slaves"]
    width = parameters["address_width"]
    base = parameters["base_address"]
    waits = parameters["wait_cycles"]
    error_enabled = str(parameters["error_response"]).lower()
    declarations = f'''  constant APB_SLAVES : positive := {slaves};
  constant APB_BASE : natural := {base};
  constant APB_REGION_BYTES : positive := 4096;
  constant APB_WAIT_CYCLES : natural := {waits};
  constant APB_ERROR_ENABLED : boolean := {error_enabled};
  type apb_memory_type is array (0 to APB_SLAVES*1024-1) of std_logic_vector(31 downto 0);
  signal apb_memory : apb_memory_type := (others => (others => '0'));
  signal apb_paddr : std_logic_vector({width-1} downto 0);
  signal apb_psel, apb_pready, apb_pslverr : std_logic_vector(APB_SLAVES-1 downto 0) := (others => '0');
  signal apb_penable, apb_pwrite : std_logic;
  signal apb_pwdata : std_logic_vector(31 downto 0);
  signal apb_pprot : std_logic_vector(2 downto 0);
  signal apb_pstrb : std_logic_vector(3 downto 0);
'''
    for index in range(slaves):
        declarations += f"  signal apb_prdata_{index} : std_logic_vector(31 downto 0) := (others => '0');\n"

    prdata_clear = "\n".join(
        f"      apb_prdata_{index} <= (others => '0');" for index in range(slaves))
    prdata_select = "\n".join(
        f"          if selected = {index} then apb_prdata_{index} <= apb_memory(word_index); end if;"
        for index in range(slaves))
    statements = f'''  apb_responder : process
    variable remaining, selected, word_index : natural := 0;
    variable ready_value, error_value : std_logic_vector(APB_SLAVES-1 downto 0);
  begin
    loop
      wait until falling_edge(aclk);
      ready_value := (others => '0');
      error_value := (others => '0');
{prdata_clear}
      if aresetn = '0' then
        remaining := 0;
      elsif not is_x(apb_psel) and unsigned(apb_psel) /= 0 then
        selected := 0;
        for i in 0 to APB_SLAVES-1 loop
          if apb_psel(i) = '1' then selected := i; end if;
        end loop;
        word_index := (to_integer(unsigned(apb_paddr))-APB_BASE)/4;
        if apb_penable = '0' then
          remaining := APB_WAIT_CYCLES;
        else
{prdata_select}
          if remaining = 0 then
            ready_value(selected) := '1';
            if APB_ERROR_ENABLED and
               (to_integer(unsigned(apb_paddr))-APB_BASE) mod APB_REGION_BYTES = 4092 then
              error_value(selected) := '1';
            end if;
          else
            remaining := remaining-1;
          end if;
        end if;
      end if;
      apb_pready <= ready_value;
      apb_pslverr <= error_value;
    end loop;
  end process;

  apb_monitor : process
    variable have_setup : boolean := false;
    variable selected, expected_slave, word_index : natural := 0;
    variable saved_addr : std_logic_vector(apb_paddr'range);
    variable saved_write : std_logic;
    variable saved_data : std_logic_vector(31 downto 0);
    variable saved_strb : std_logic_vector(3 downto 0);
    variable saved_prot : std_logic_vector(2 downto 0);
    variable merged, lane_mask : std_logic_vector(31 downto 0);
  begin
    loop
      wait until rising_edge(aclk);
      if aresetn = '0' then
        have_setup := false;
      elsif unsigned(apb_psel) /= 0 then
        assert not is_x(apb_psel) and not is_x(apb_paddr) and
               (apb_penable = '0' or apb_penable = '1') and
               (apb_pwrite = '0' or apb_pwrite = '1')
          report "AXILITE_SELF_CHECK_STATUS: FAIL unknown APB control" severity failure;
        assert unsigned(apb_psel) /= 0 and
               (unsigned(apb_psel) and (unsigned(apb_psel)-1)) = 0
          report "AXILITE_SELF_CHECK_STATUS: FAIL APB PSEL is not one-hot" severity failure;
        selected := 0;
        for i in 0 to APB_SLAVES-1 loop
          if apb_psel(i) = '1' then selected := i; end if;
        end loop;
        expected_slave := (to_integer(unsigned(apb_paddr))-APB_BASE)/APB_REGION_BYTES;
        assert expected_slave < APB_SLAVES and selected = expected_slave
          report "AXILITE_SELF_CHECK_STATUS: FAIL APB address routed to wrong slave" severity failure;
        if apb_penable = '0' then
          assert not have_setup
            report "AXILITE_SELF_CHECK_STATUS: FAIL repeated APB setup" severity failure;
          have_setup := true;
          saved_addr := apb_paddr; saved_write := apb_pwrite;
          saved_data := apb_pwdata; saved_strb := apb_pstrb; saved_prot := apb_pprot;
        else
          assert have_setup
            report "AXILITE_SELF_CHECK_STATUS: FAIL APB access without setup" severity failure;
          assert apb_paddr = saved_addr and apb_pwrite = saved_write and
                 apb_pwdata = saved_data and apb_pstrb = saved_strb and apb_pprot = saved_prot
            report "AXILITE_SELF_CHECK_STATUS: FAIL APB control changed during access" severity failure;
          if apb_pwrite = '1' then
            assert apb_pprot = p_s_axi_awprot and apb_pstrb = wstrb
              report "AXILITE_SELF_CHECK_STATUS: FAIL APB4 write attributes" severity failure;
          else
            assert apb_pprot = p_s_axi_arprot and apb_pstrb = "0000"
              report "AXILITE_SELF_CHECK_STATUS: FAIL APB4 read attributes" severity failure;
          end if;
          if apb_pready(selected) = '1' then
            if apb_pwrite = '1' and apb_pslverr(selected) = '0' then
              word_index := (to_integer(unsigned(apb_paddr))-APB_BASE)/4;
              merged := apb_memory(word_index);
              for lane in 0 to 3 loop
                if apb_pstrb(lane) = '1' then
                  lane_mask := (others => '0');
                  lane_mask(lane*8+7 downto lane*8) := (others => '1');
                  merged := (merged and not lane_mask) or (apb_pwdata and lane_mask);
                end if;
              end loop;
              apb_memory(word_index) <= merged;
            end if;
            have_setup := false;
          end if;
        end if;
      else
        assert apb_penable = '0'
          report "AXILITE_SELF_CHECK_STATUS: FAIL APB PENABLE without PSEL" severity failure;
      end if;
    end loop;
  end process;
'''
    mappings = [
        "m_apb_paddr => apb_paddr", "m_apb_psel => apb_psel",
        "m_apb_penable => apb_penable", "m_apb_pwrite => apb_pwrite",
        "m_apb_pwdata => apb_pwdata", "m_apb_pready => apb_pready",
        "m_apb_pslverr => apb_pslverr", "m_apb_pprot => apb_pprot",
        "m_apb_pstrb => apb_pstrb",
    ]
    for index in range(slaves):
        port = "m_apb_prdata" if index == 0 else f"m_apb_prdata{index+1}"
        mappings.append(f"{port} => apb_prdata_{index}")
    return declarations, statements, tuple(mappings)

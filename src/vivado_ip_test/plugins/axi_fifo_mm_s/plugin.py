from vivado_ip_test.plugins.common.axilite.plugin import AxiLiteIpPlugin
from vivado_ip_test.plugins.common.axilite.spec import AxiLiteSpec
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.axi_fifo_mm_s.reference import AxiFifoModel
from vivado_ip_test.plugins.axi_fifo_mm_s.vectors import prepare_operations


DEPTHS = {512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072}


def _stream_extension(has_keep, destination_width):
    declarations = [
        "  signal txd_tvalid, txd_tready, txd_tlast : std_logic := '0';",
        "  signal rxd_tvalid, rxd_tready, rxd_tlast : std_logic := '0';",
        "  signal txd_tdata, rxd_tdata : std_logic_vector(31 downto 0) := (others => '0');",
        "  signal stream_gate : std_logic := '0';",
        "  signal stream_cycle : natural := 0;",
    ]
    mappings = [
        "axi_str_txd_tvalid => txd_tvalid", "axi_str_txd_tready => txd_tready",
        "axi_str_txd_tlast => txd_tlast", "axi_str_txd_tdata => txd_tdata",
        "axi_str_rxd_tvalid => rxd_tvalid", "axi_str_rxd_tready => rxd_tready",
        "axi_str_rxd_tlast => rxd_tlast", "axi_str_rxd_tdata => rxd_tdata",
    ]
    assignments = [
        "  txd_tready <= rxd_tready and stream_gate;",
        "  rxd_tvalid <= txd_tvalid and stream_gate;",
        "  rxd_tlast <= txd_tlast;",
        "  rxd_tdata <= txd_tdata;",
    ]
    hold_fields = "txd_tdata = held_data and txd_tlast = held_last"
    if has_keep:
        declarations.extend((
            "  signal txd_tkeep, rxd_tkeep : std_logic_vector(3 downto 0) := (others => '0');",
        ))
        mappings.extend(("axi_str_txd_tkeep => txd_tkeep", "axi_str_rxd_tkeep => rxd_tkeep"))
        assignments.append("  rxd_tkeep <= txd_tkeep;")
        hold_fields += " and txd_tkeep = held_keep"
    if destination_width:
        declarations.append(
            f"  signal txd_tdest, rxd_tdest : std_logic_vector({destination_width-1} downto 0) := (others => '0');")
        mappings.extend(("axi_str_txd_tdest => txd_tdest", "axi_str_rxd_tdest => rxd_tdest"))
        assignments.append("  rxd_tdest <= txd_tdest;")
        hold_fields += " and txd_tdest = held_dest"
    variables = [
        "    variable held : boolean := false;",
        "    variable held_data : std_logic_vector(31 downto 0);",
        "    variable held_last : std_logic;",
    ]
    remember = ["        held_data := txd_tdata;", "        held_last := txd_tlast;"]
    if has_keep:
        variables.append("    variable held_keep : std_logic_vector(3 downto 0);")
        remember.append("        held_keep := txd_tkeep;")
    if destination_width:
        variables.append(
            f"    variable held_dest : std_logic_vector({destination_width-1} downto 0);")
        remember.append("        held_dest := txd_tdest;")
    statements = "\n".join(assignments) + f'''\n  stream_backpressure : process
  begin
    loop
      wait until rising_edge(aclk);
      if aresetn = '0' then
        stream_cycle <= 0;
        stream_gate <= '0';
      else
        stream_cycle <= stream_cycle+1;
        if stream_cycle mod 11 = 3 or stream_cycle mod 11 = 4 or stream_cycle mod 11 = 8 then
          stream_gate <= '0';
        else
          stream_gate <= '1';
        end if;
      end if;
    end loop;
  end process;

  stream_monitor : process
{chr(10).join(variables)}
  begin
    loop
      wait until rising_edge(aclk);
      wait for 1 ps;
      if aresetn = '0' then
        held := false;
      else
        assert txd_tvalid = '0' or txd_tvalid = '1'
          report "AXILITE_SELF_CHECK_STATUS: FAIL unknown TX stream valid" severity failure;
        if txd_tvalid = '1' then
          assert not is_x(txd_tdata) and (txd_tlast = '0' or txd_tlast = '1')
            report "AXILITE_SELF_CHECK_STATUS: FAIL unknown TX stream payload" severity failure;
        end if;
        if held then
          assert txd_tvalid = '1' and {hold_fields}
            report "AXILITE_SELF_CHECK_STATUS: FAIL TX stream changed under backpressure" severity failure;
        end if;
        held := txd_tvalid = '1' and txd_tready = '0';
        if held then
{chr(10).join(remember)}
        end if;
      end if;
    end loop;
  end process;
'''
    return "\n".join(declarations), tuple(mappings), statements


class AxiFifoMmSPlugin(AxiLiteIpPlugin):
    ip_type = ip_name = "axi_fifo_mm_s"
    version = "4.3"

    def describe(self, p):
        validate_parameters(p, {"tx_depth": range(512, 131073), "rx_depth": range(512, 131073),
                                "has_keep": bool, "destination_width": range(0, 5),
                                "use_xpm": bool})
        if p["tx_depth"] not in DEPTHS or p["rx_depth"] not in DEPTHS:
            raise PluginError("AXI4-Stream FIFO depth is not a supported power-of-two setting")
        declarations, mappings, statements = _stream_extension(
            p["has_keep"], p["destination_width"])
        settings = {
            "C_S_AXI_PROTOCOL": "AXI4LITE", "C_S_AXI_DATA_WIDTH": 32,
            "C_S_AXI4_DATA_WIDTH": 32, "C_DATA_INTERFACE_TYPE": 0,
            "C_USE_TX_DATA": 1, "C_USE_RX_DATA": 1, "C_USE_TX_CTRL": 0,
            "C_TX_FIFO_DEPTH": p["tx_depth"], "C_RX_FIFO_DEPTH": p["rx_depth"],
            "C_USE_TX_CUT_THROUGH": 0, "C_USE_RX_CUT_THROUGH": False,
            "C_HAS_AXIS_TKEEP": p["has_keep"], "C_HAS_AXIS_TSTRB": False,
            "C_HAS_AXIS_TDEST": bool(p["destination_width"]),
            "C_AXIS_TDEST_WIDTH": p["destination_width"] or 4,
            "C_HAS_AXIS_TID": False, "C_HAS_AXIS_TUSER": False,
            "C_SELECT_XPM": int(p["use_xpm"]), "TX_ENABLE_ECC": 0, "RX_ENABLE_ECC": 0,
        }
        model = {
            "C_S_AXI_ADDR_WIDTH": 32, "C_S_AXI_DATA_WIDTH": 32, "C_S_AXI4_DATA_WIDTH": 32,
            "C_DATA_INTERFACE_TYPE": 0, "C_USE_TX_DATA": 1, "C_USE_RX_DATA": 1,
            "C_USE_TX_CTRL": 0, "C_TX_FIFO_DEPTH": p["tx_depth"],
            "C_RX_FIFO_DEPTH": p["rx_depth"], "C_USE_TX_CUT_THROUGH": 0,
            "C_USE_RX_CUT_THROUGH": 0, "C_HAS_AXIS_TKEEP": int(p["has_keep"]),
            "C_HAS_AXIS_TSTRB": 0, "C_HAS_AXIS_TDEST": int(bool(p["destination_width"])),
            "C_AXIS_TDEST_WIDTH": p["destination_width"] or 4,
            "C_HAS_AXIS_TID": 0, "C_HAS_AXIS_TUSER": 0,
        }
        generated = [Port("word", 32)]
        if p["destination_width"]:
            generated.append(Port("destination", p["destination_width"]))
        metadata_inputs = [
            Port("s_axi_aresetn", scalar=True), Port("s_axi_awaddr", 32),
            Port("s_axi_awvalid", scalar=True), Port("s_axi_wdata", 32),
            Port("s_axi_wstrb", 4), Port("s_axi_wvalid", scalar=True),
            Port("s_axi_bready", scalar=True), Port("s_axi_araddr", 32),
            Port("s_axi_arvalid", scalar=True), Port("s_axi_rready", scalar=True),
            Port("axi_str_txd_tready", scalar=True), Port("axi_str_rxd_tvalid", scalar=True),
            Port("axi_str_rxd_tlast", scalar=True), Port("axi_str_rxd_tdata", 32),
        ]
        metadata_outputs = [
            Port("s_axi_awready", scalar=True), Port("s_axi_wready", scalar=True),
            Port("s_axi_bresp", 2), Port("s_axi_bvalid", scalar=True),
            Port("s_axi_arready", scalar=True), Port("s_axi_rdata", 32),
            Port("s_axi_rresp", 2), Port("s_axi_rvalid", scalar=True),
            Port("interrupt", scalar=True), Port("mm2s_prmry_reset_out_n", scalar=True),
            Port("s2mm_prmry_reset_out_n", scalar=True),
            Port("axi_str_txd_tvalid", scalar=True), Port("axi_str_txd_tlast", scalar=True),
            Port("axi_str_txd_tdata", 32), Port("axi_str_rxd_tready", scalar=True),
        ]
        if p["has_keep"]:
            metadata_inputs.append(Port("axi_str_rxd_tkeep", 4))
            metadata_outputs.append(Port("axi_str_txd_tkeep", 4))
        if p["destination_width"]:
            metadata_inputs.append(Port("axi_str_rxd_tdest", p["destination_width"]))
            metadata_outputs.append(Port("axi_str_txd_tdest", p["destination_width"]))
        metadata_spec = CycleSpec(tuple(metadata_inputs), tuple(metadata_outputs), settings, model,
                                  lambda: None, clock="s_axi_aclk")
        parameters = dict(p)
        return AxiLiteSpec(
            32, (), (Port("interrupt", scalar=True), Port("mm2s_prmry_reset_out_n", scalar=True),
                     Port("s2mm_prmry_reset_out_n", scalar=True)), tuple(generated), settings, model,
            lambda: AxiFifoModel(parameters),
            lambda samples: prepare_operations(samples, parameters),
            settle_cycles=96, reset_cycles=32, minimum_ip_revision=7,
            metadata_spec=metadata_spec,
            extra_mappings=mappings, testbench_declarations=declarations,
            testbench_statements=statements,
        )

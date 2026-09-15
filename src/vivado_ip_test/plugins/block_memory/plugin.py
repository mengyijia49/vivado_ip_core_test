from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.block_memory.reference import BlockMemoryModel
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin


class BlockMemoryPlugin(CycleIpPlugin):
    ip_type = "block_memory"
    ip_name = "blk_mem_gen"
    version = "8.4"

    def describe(self, p):
        modes = {"WRITE_FIRST", "READ_FIRST", "NO_CHANGE"}
        types = ("Single_Port_RAM", "Simple_Dual_Port_RAM", "True_Dual_Port_RAM")
        validate_parameters(p, {"width": range(1, 257), "depth": range(2, 4097),
            "memory_type": set(types), "write_mode_a": modes, "write_mode_b": modes,
            "output_register": bool, "register_enable": bool, "sync_reset": bool,
            "reset_memory_latch": bool, "byte_size": range(0, 10),
            "initial_value": range(0, 1 << 256), "output_reset_value": range(0, 1 << 256)})
        if p["byte_size"] not in (0, 8, 9) or p["byte_size"] and p["width"] % p["byte_size"]:
            raise PluginError("Block memory bytes must be 8 or 9 bits and divide the data width")
        if p["register_enable"] and not p["output_register"]:
            raise PluginError("REGCE requires an output register")
        if p["reset_memory_latch"] and not (p["output_register"] and p["sync_reset"]):
            raise PluginError("Reset memory latch requires the output register and reset pin")
        if not p["sync_reset"] and p["output_reset_value"]:
            raise PluginError("Disabled reset uses the canonical output_reset_value=0")
        if p["memory_type"] != "True_Dual_Port_RAM" and p["write_mode_b"] != "READ_FIRST":
            raise PluginError("Unused B write mode must be READ_FIRST")
        if p["memory_type"] == "Simple_Dual_Port_RAM" and p["write_mode_a"] != "READ_FIRST":
            raise PluginError("The current 7-series synchronous SDP backend uses READ_FIRST")
        if p["byte_size"] and "NO_CHANGE" in (p["write_mode_a"], p["write_mode_b"]):
            raise PluginError("PG058 excludes NO_CHANGE with byte writes")
        limit = (1 << p["width"]) - 1
        for key in ("initial_value", "output_reset_value"):
            if p[key] > limit:
                raise PluginError(f"{key} does not fit the memory width")
        dual = p["memory_type"] != "Single_Port_RAM"
        readers = ("b",) if p["memory_type"] == "Simple_Dual_Port_RAM" else (("a", "b") if dual else ("a",))
        writers = ("a", "b") if p["memory_type"] == "True_Dual_Port_RAM" else ("a",)
        lanes = p["width"] // p["byte_size"] if p["byte_size"] else 1
        inputs, settings, models, neutral, idle = [], {}, {}, {}, {}
        for port in (("a", "b") if dual else ("a",)):
            cap = port.upper()
            inputs += [Port(f"addr{port}", (p["depth"] - 1).bit_length(), maximum=p["depth"] - 1),
                       Port(f"en{port}", scalar=True)]
            neutral[f"en{port}"] = 1
            idle[f"en{port}"] = 0
            settings[f"Enable_{cap}"] = f"Use_EN{cap}_Pin"
            if port in writers:
                inputs += [Port(f"din{port}", p["width"]), Port(f"we{port}", lanes)]
                idle[f"we{port}"] = 0
                settings[f"Write_Width_{cap}"] = p["width"]
                settings[f"Operating_Mode_{cap}"] = p[f"write_mode_{port}"]
                models.update({f"C_WRITE_WIDTH_{cap}": p["width"], f"C_WRITE_MODE_{cap}": p[f"write_mode_{port}"]})
            if port in readers:
                settings.update({f"Read_Width_{cap}": p["width"], f"Use_RST{cap}_Pin": p["sync_reset"],
                    f"Use_REGCE{cap}_Pin": p["register_enable"], f"Reset_Priority_{cap}": "CE",
                    f"Reset_Memory_Latch_{cap}": p["reset_memory_latch"],
                    f"Output_Reset_Value_{cap}": format(p["output_reset_value"], "x"),
                    f"Register_Port{cap}_Output_of_Memory_Primitives": p["output_register"],
                    f"Register_Port{cap}_Output_of_Memory_Core": False})
                models.update({f"C_READ_WIDTH_{cap}": p["width"], f"C_HAS_RST{cap}": int(p["sync_reset"]),
                    f"C_HAS_REGCE{cap}": int(p["register_enable"]), f"C_RST_PRIORITY_{cap}": "CE",
                    f"C_RSTRAM_{cap}": int(p["reset_memory_latch"]),
                    f"C_HAS_MEM_OUTPUT_REGS_{cap}": int(p["output_register"]),
                    f"C_HAS_MUX_OUTPUT_REGS_{cap}": 0,
                    f"C_INIT{cap}_VAL": format(p["output_reset_value"], "x")})
                for name, enabled in ((f"rst{port}", p["sync_reset"]), (f"regce{port}", p["register_enable"])):
                    if enabled:
                        inputs.append(Port(name, scalar=True))
                        neutral[name] = int(name.startswith("regce"))
                        idle[name] = 0
        if p["memory_type"] == "Simple_Dual_Port_RAM":
            settings.update({"Register_PortA_Output_of_Memory_Primitives": False, "Use_RSTA_Pin": False})
        write_enable = (1 << lanes) - 1

        def prefix():
            if p["sync_reset"]:
                yield {f"rst{port}": 1 for port in readers}
                yield {}
            for phase in ("initial_read", "write", "read", "invert", "read"):
                for address in range(p["depth"]):
                    value = (address * 0x9E3779B1) & limit
                    row = {"addra": address, "dina": value ^ limit if phase == "invert" else value,
                           "wea": write_enable if phase in {"write", "invert"} else 0}
                    if dual:
                        row["addrb"] = p["depth"] - 1 - address
                    yield row
            for address in sorted({0, p["depth"] // 2, p["depth"] - 1}):
                for lane in range(lanes):
                    for port in writers:
                        row = {f"addr{port}": address, f"din{port}": limit, f"we{port}": 1 << lane}
                        if dual:
                            row.update({"addra": address, "addrb": address})
                        yield row
                        yield {f"addr{r}": address for r in sorted(set(readers + writers))}
                if len(writers) == 2:
                    for lane in range(lanes):
                        common = {"addra": address, "addrb": address}
                        if lanes > 1:
                            yield {**common, "wea": 1 << lane, "web": 1 << ((lane + 1) % lanes),
                                   "dina": limit, "dinb": 0}
                            yield common
                        yield {**common, "wea": 1 << lane, "web": 1 << lane,
                               "dina": limit, "dinb": 0}
                        yield common
                        yield {**common, "wea": write_enable, "dina": (address * 0x9E3779B1) & limit}
                        yield common

        def suffix():
            for address in range(p["depth"]):
                yield {f"addr{port}": address for port in sorted(set(readers + writers))}
        return CycleSpec(tuple(inputs), tuple(Port(f"dout{r}", p["width"]) for r in readers),
            settings={"Interface_Type": "Native", "Memory_Type": p["memory_type"],
                "Write_Depth_A": p["depth"], "Use_Byte_Write_Enable": bool(p["byte_size"]),
                **({"Byte_Size": p["byte_size"]} if p["byte_size"] else {}),
                "Load_Init_File": False, "Fill_Remaining_Memory_Locations": True,
                "Remaining_Memory_Locations": format(p["initial_value"], "x"),
                "Assume_Synchronous_Clk": dual, "EN_SAFETY_CKT": False, "Reset_Type": "SYNC",
                "Pipeline_Stages": 0, **settings},
            model_parameters={"C_MEM_TYPE": types.index(p["memory_type"]), "C_WRITE_DEPTH_A": p["depth"],
                "C_USE_DEFAULT_DATA": 1, "C_DEFAULT_DATA": format(p["initial_value"], "x"),
                "C_USE_BYTE_WEA": int(bool(p["byte_size"])), "C_WEA_WIDTH": lanes,
                "C_COMMON_CLK": int(dual), "C_EN_SAFETY_CKT": 0, **models},
            model_parameter_radices={"C_DEFAULT_DATA": 16, "C_INITA_VAL": 16, "C_INITB_VAL": 16},
            model_factory=lambda: BlockMemoryModel(p), clock="clka", clock_aliases=("clkb",) if dual else (),
            masked_outputs=True, neutral=neutral, idle_values=idle, prefix=prefix,
            suffix=suffix, flush_cycles=2 + int(p["output_register"]))

def directed_sequence(parameters):
    data_mask = (1 << parameters["data_width"]) - 1
    user_mask = (1 << parameters["address_user_width"]) - 1
    id_mask = (1 << parameters["id_width"]) - 1
    common = {
        "aresetn": 1, "aclken": 1,
        "s_axi_awid": id_mask, "s_axi_awaddr": 0x12345678,
        "s_axi_awlen": 3, "s_axi_awsize": parameters["data_width"].bit_length() - 4,
        "s_axi_awburst": 1, "s_axi_awlock": 0, "s_axi_awcache": 3,
        "s_axi_awprot": 5, "s_axi_awqos": 9, "s_axi_awuser": user_mask,
        "s_axi_arid": (id_mask ^ 1) & id_mask, "s_axi_araddr": 0x89ABCDF0,
        "s_axi_arlen": 1, "s_axi_arsize": parameters["data_width"].bit_length() - 4,
        "s_axi_arburst": 2, "s_axi_arlock": 1, "s_axi_arcache": 12,
        "s_axi_arprot": 2, "s_axi_arqos": 6, "s_axi_aruser": user_mask ^ 1,
        "s_axi_wdata": data_mask ^ 0x55, "s_axi_wstrb": (1 << (parameters["data_width"] // 8)) - 1,
        "s_axi_wlast": 1, "m_axi_bid": (id_mask ^ 2) & id_mask, "m_axi_bresp": 2,
        "m_axi_rid": (id_mask ^ 3) & id_mask, "m_axi_rdata": data_mask ^ 0xAA,
        "m_axi_rresp": 1, "m_axi_rlast": 1,
    }
    yield {"aresetn": 0, "aclken": 1}
    for channel, ready in (("aw", "m_axi_awready"), ("w", "m_axi_wready"),
                           ("ar", "m_axi_arready")):
        yield {**common, f"s_axi_{channel}valid": 1, ready: 0}
        yield {**common, f"s_axi_{channel}valid": 1, ready: 1}
    for channel, ready in (("b", "s_axi_bready"), ("r", "s_axi_rready")):
        yield {**common, f"m_axi_{channel}valid": 1, ready: 0}
        yield {**common, f"m_axi_{channel}valid": 1, ready: 1}
    yield {
        **common, "s_axi_awvalid": 1, "s_axi_wvalid": 1, "s_axi_bready": 1,
        "s_axi_arvalid": 1, "s_axi_rready": 1, "m_axi_awready": 1,
        "m_axi_wready": 1, "m_axi_bvalid": 1, "m_axi_arready": 1,
        "m_axi_rvalid": 1,
    }

# AXI-Stream 寄存器片

IP：`xilinx.com:ip:axis_register_slice:1.1`。只做行为仿真。

```bash
python3 scripts/run_all.py --ip-type axis_register_slice
```

参数支持 1 至 64 字节数据，可选 LAST、KEEP、STRB、ID、DEST、USER。
`register_mode` 为 Default、Bypass、Fully_Registered、Light_Weight。
对应 REG_CONFIG 为 1、0、8、7，已核对本机 Catalog 的枚举。
没有启用 ACLKEN 和跨 SLR 模式。

不同模式的延迟、接收间隔可以不同，检查只按实际握手比较数据和顺序，
暂停期间仍检查输出保持。共用规则与限制见 [流接口自检](../../protocols/axis_stream.md)。
各模式含义见 [PG085](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/Advanced-Properties)。

配置分别在 `configs/ip/axis_register_slice/regression.json` 和 `extended.json`。
常用回归包括四种模式；大矩阵不默认运行。

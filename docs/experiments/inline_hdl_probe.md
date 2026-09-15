# Inline HDL 创建探测

2026-09-15，Vivado 2025.2。
编号 `2026-09-15_04-51-25_UTC+0800_8da4584f`，三组创建成功，当时尚未运行功能自检。

| 模块 | 参数 | 实际接口 |
| --- | --- | --- |
| ilconcat:1.0 | 3 路，宽度 1/7/33 | In0/In1/In2 输入，dout 为 41 位 |
| ilslice:1.0 | 输入 4096 位，截取 255 至 247 | Din 输入，Dout 为 9 位 |
| ilconstant:1.0 | 128 位，值为最高位与最低位同时为 1 | 只有 128 位 dout |

诊断入口为 `tcl/diagnostics/inspect_inline_hdl.tcl`，参数是：

```text
run_dir inline_name CONFIG.name value ...
```

本次通过 Python 的 VivadoBatchRunner 调用 batch Tcl，没有 GUI、综合或网表仿真。
实际参数保存在各运行目录的 `parameters.json`，完整命令保存在对应 `create.log`。
工程位于 `runs/framework/catalog/<编号>/<模块>/inline/`，
日志位于 `runs/logs/framework/catalog/<编号>/<模块>/inline/`。

创建命令使用 `create_bd_cell -type inline_hdl -vlnv xilinx.com:inline_hdl:<名称>:1.0 core`。
[UG835](https://docs.amd.com/r/2024.2-English/ug835-vivado-tcl-commands/create_bd_cell)说明
Inline HDL 保存在 Block Design 中，不具有独立的磁盘 IP 实例。
本次也没有生成独立 XCI，实际配置和接线在 `.bd` 中，仿真 HDL 由 Vivado 生成。

上述内容是最初的创建探测。之后已补齐 `.bd` 的模块标识、有效参数、端口和接线核对，
三个模块均已接入公共创建、自检、仿真和归档流程，见各自的[使用说明](../ip/catalog.md)。
旧版 xlconcat/xlslice/xlconstant 的 PASS 仍不属于这三个替代模块。
后续 ilconcat 另做了 128 路独立 VHDL 对照，六次观察均匹配，
见[端口边界记录](../ip/xlconcat/port_128_issue.md)。
新一轮还创建了 `DIN_WIDTH=4096, DIN_FROM=4095, DIN_TO=4095` 的 ilslice，
编号 `2026-09-15_05-38-08_UTC+0800_76d20837`，实际参数和生成端口均符合要求。
XML 中的静态 255 上限不是这里的最终范围，插件按输入宽度检查高低位。

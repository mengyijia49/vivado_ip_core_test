# LMB BRAM Interface Controller 自检

本模块测试 `lmb_bram_if_cntlr:4.0`。它连接 MicroBlaze 的 Local Memory Bus 和外部
BRAM 端口。测试不依赖 MicroBlaze，也不把 Vivado 输出当作期望值。

Python 模型按周期计算地址是否命中、保护属性是否允许访问，以及 BRAM 侧应该出现的
地址、使能、字节写使能和写数据。testbench 同时检查 LMB 的 `Ready`、`UE`、读数据和
BRAM 侧全部信号。定向输入覆盖地址范围首尾、范围外地址、全部字节使能、读写冲突、
复位期间请求和四种保护属性。随机输入用于补充协议边界组合。

参数包括 32/64 位数据、32/64 位地址、4 KiB 到 1 MiB 地址范围、只读、整字写、任意
字节写以及可选保护掩码。常用配置有 4 组，扩展配置有 68 组。

当前固定使用单个 LMB、标准协议和无 ECC。多 LMB 仲裁、ECC、故障注入和 AXI 控制
寄存器尚未接入，不能把这些功能算作已覆盖。

本模块只运行行为仿真。代表配置通过以后，也只能说明这些输入下没有发现差异，不能说明
控制器不存在其他问题。

2026-09-22 在 Vivado 2026.1 运行四组常用配置，12 个阶段全部通过。
详见[全量运行记录](../../experiments/vivado_2026_full_regression.md)。

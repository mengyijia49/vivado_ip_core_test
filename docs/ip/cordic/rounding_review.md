# CORDIC 舍入差异审查

2026-09-22 在 Vivado 2026.1 的常用配置运行中，五组平方根配置出现数学参考值与仿真输出不同：
`cordic_sqrt_u8_nearest`、`cordic_sqrt_f9_17_nearest`、
`cordic_sqrt_f17_8_even`、`cordic_sqrt_f16_exhaustive`、
`cordic_sqrt_f48_full`。原始结果见[全量运行记录](../../experiments/vivado_2026_full_regression.md)。

Python 参考按精确平方根和指定舍入模式计算，尚不是厂商位精确模型。
IP 内部精度有限，最终结果可能与直接对精确数学值舍入不同。
因此这些失败只表示数值差异，不能据此计作五个 IP bug。
下一步要核对当前手册对内部精度和输出误差的保证，再决定如何评分。

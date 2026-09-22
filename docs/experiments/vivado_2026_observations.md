# Vivado 2026.1 问题观察

2026-09-22 使用 Vivado 2026.1、Artix-7 `xc7a35tcsg324-1` 做行为仿真。
本次针对 10 类异常做了配置运行或独立 VHDL 观察，不是 10 个已确认 bug。
厂商确认数量仍为 0。

| 线索 | 2026.1 结果 | 本次证据 |
| --- | --- | --- |
| 累加器 CE/BYPASS | 自检数值差异仍在；规范优先级未定 | [失败摘要](../../evidence/vivado_2026_1/observations/2026-09-22_12-10-15_UTC+0800_a223367f/accumulator/failure.json) |
| 复数乘法长延迟 | 自检失败；固定 VHDL 第 80 拍提前输出 1 | [独立仿真日志](../../evidence/vivado_2026_1/observations/2026-09-22_12-23-30_UTC+0800_1721014/complex_multiplier/literal_probe_sim.process.log) |
| TMR 锁步比较器 | 厂商 VHDL 展开仍报四位接一位 | [独立仿真日志](../../evidence/vivado_2026_1/observations/2026-09-22_12-24-06_UTC+0800_1725142/tmr_voter/literal_probe_sim.process.log) |
| 旧版 xlconcat 128 路 | 128 路五种非零输入不符；127 路和 Inline 128 路对照通过 | [旧版 128 路](../../evidence/vivado_2026_1/observations/2026-09-22_12-22-18_UTC+0800_b1e61770/xlconcat/n128_observations.json)、[新版对照](../../evidence/vivado_2026_1/observations/2026-09-22_12-22-40_UTC+0800_fa081308/ilconcat/n128_observations.json) |
| 浮点低延迟乘法 | 固定 VHDL 五个样例不符；两种速度优化对照通过 | [低延迟](../../evidence/vivado_2026_1/observations/2026-09-22_12-20-24_UTC+0800_7ed4ef68/floating_point/low_latency_summary.json)、[速度优化](../../evidence/vivado_2026_1/observations/2026-09-22_12-20-51_UTC+0800_77f3065a/floating_point/speed_optimized_max_summary.json) |
| AXI GPIO 寄存器 | 独立 VHDL 观察到方向切换和未启用寄存器读回差异 | [观测值](../../evidence/vivado_2026_1/observations/2026-09-22_12-14-26_UTC+0800_00f9d856/axi_gpio/observations.json) |
| AXI INTC ISR | 预编译库和直接编译 HDL 均丢失旧位 | [直接编译摘要](../../evidence/vivado_2026_1/observations/2026-09-22_12-16-04_UTC+0800_339fde83/axi_intc/isr_fresh_source_summary.json)、[预编译摘要](../../evidence/vivado_2026_1/observations/2026-09-22_12-16-30_UTC+0800_681743cf/axi_intc/isr_precompiled_summary.json) |
| AXI INTC ME | 两条模型路径均在清除 ME 后保留已有效的 IRQ | [预编译摘要](../../evidence/vivado_2026_1/observations/2026-09-22_12-16-56_UTC+0800_61892d25/axi_intc/me_precompiled_summary.json)、[直接编译摘要](../../evidence/vivado_2026_1/observations/2026-09-22_12-17-16_UTC+0800_f6f38e7c/axi_intc/me_fresh_source_summary.json) |
| FIR 全精度 | 两种架构的四项负系数测试符号翻转；两项正系数对照通过 | [负系数](../../evidence/vivado_2026_1/observations/2026-09-22_12-18-39_UTC+0800_1380e4ff/fir_compiler/negative_power_systolic_summary.json)、[正系数对照](../../evidence/vivado_2026_1/observations/2026-09-22_12-19-29_UTC+0800_ad024b9b/fir_compiler/positive_systolic_summary.json) |
| Mailbox TLAST | 分布式 RAM、块 RAM 两组仿真日志均报 TLAST 为 0 而期望 1 | [分布式 RAM 日志](../../evidence/vivado_2026_1/observations/2026-09-22_12-13-24_UTC+0800_e52ddfa9/mailbox/d16_distributed_sim.process.log)、[块 RAM 日志](../../evidence/vivado_2026_1/observations/2026-09-22_12-13-24_UTC+0800_e52ddfa9/mailbox/d32_block_sim.process.log) |

表中时间均为当天本地时间，完整运行编号在下面。`SIMULATION_FAILED` 需要结合仿真日志看；
它既可能是数值比较失败，也可能是 XSim 展开失败。独立 VHDL 中的测试命令返回非零，
是因为它坚持报告不符，不能把非零退出码直接解释成环境故障。

## 运行位置

- 多 IP 批次：`reports/history/2026.1/2026-09-22_12-10-15_UTC+0800_a223367f/`。
- Mailbox 批次：`reports/history/2026.1/2026-09-22_12-13-24_UTC+0800_e52ddfa9/`。
- 独立复现：`runs/framework/<复现名称>/<运行编号>/`、`reports/framework/<复现名称>/<运行编号>/`。
- 复数乘法和 TMR 的独立复现放在 `runs/framework/<复现名称>/2026.1/<运行编号>/`。

`runs/` 和 `reports/` 不整体提交。公开副本见[2026.1 观察证据](../../evidence/vivado_2026_1/observations/)。
本地完整工程仍在上述目录，公开副本保留报告、关键观察、日志和哈希。

478 组常用配置全量运行中，AXI-to-LMB 的两组参数出现文件校验差异；
原因仍在排查，见[全量运行记录](vivado_2026_full_regression.md)。
表中 10 项也还需核对 2026.1 文档、已知问题、影响范围和真实硬件；
尤其 GPIO 和累加器存在规范解释疑点，不能把本机复现直接写成厂商 bug。

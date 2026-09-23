# 待确认问题

截至 2026-09-23，原有 13 条线索中有 2 条已查明是测试框架问题，剩余 11 条待确认。
这 11 条来自 Vivado 2026.1 行为仿真，
厂商确认的 bug 仍为 0。每行写一种现象，不按 IP 种类计数；
同一种差异在多个配置或输入下重复出现，也不重复计数。
运行编号、原始结果和对照见[2026.1 观察记录](vivado_2026_observations.md)。
478 组常用配置的整批结果见[全量运行记录](vivado_2026_full_regression.md)。

## 第一次看这些记录

IP 核可以理解为厂商提供的现成电路模块。Vivado 按你选的参数生成它，
例如生成一个 8 位输入的 FIR 滤波器，或者一个 32 位数据接口的 Mailbox。

| 文档里的词 | 在本项目中是什么意思 |
| --- | --- |
| 参数 / 配置 | 生成电路时选的设置，例如位宽、通道数、架构；一组设置是一种配置 |
| 测试输入 | 电路生成后送进去的数据或操作，例如输入 -128、向寄存器写 1 |
| 配置名 | 项目给一组参数起的名字，例如 `fp_mul64_low`；它不是另一个厂商 IP 型号 |
| testbench | 仿真中的测试程序，负责送输入、产生时钟和复位、收集输出 |
| 参考值 / golden | 根据数学公式或预期操作规则独立得到的答案；参考本身也需要核对 |
| 行为仿真 | 在电脑里运行电路模型，观察功能和信号；这里的实测指仿真观测 |
| 拍 / 周期 | 按时钟数的一步；数据可能需要等几拍才被接收或算出结果 |
| 独立复现 | 用另外写的固定测试缩小问题；只把同一套自检重跑一次不会自动变成独立复现 |

例如 FIR 的“输入宽度 8 位”是参数，“送入 -128”是测试输入。
同一参数配置可以测很多输入；换系数或换架构，则会生成不同配置。

可以先读 [FIR](../ip/fir_compiler/full_precision_issue.md)，里面用普通乘加解释数值与位宽；
再读 [GPIO](../ip/axi_gpio/direction_write_issue.md)，理解寄存器和输入输出方向；
最后读 [Mailbox](../ip/mailbox/tlast_issue.md)，理解数据、握手和包尾。
每篇都保留了全部已记录的相关参数组，并解释具体操作和结果。

## 问题列表



|  | 现象 | 触发配置与结果 | 还需确认 | 确认? |
| --- | --- | --- | --- | --- |
| 1 | [复数乘法器](../ip/complex_multiplier/latency_issue.md) | `cmul_long_pipe` 首次发现；独立 240 拍观察中，54、55 拍配置的数据提前出现，但有效信号仍延迟；自动、4、16 拍正常 | 长延迟的数据与有效信号错位，内部原因和硬件表现尚未确认 |  |
| 2 | [旧版 xlconcat](../ip/xlconcat/port_128_issue.md) | 128 路各 1 位，全 1 输入预期全 1，实际全 0；127 路及新版对照正常 | 旧版是否仍受支持 |  |
| 3 | [TMR 投票器](../ip/tmr_voter/lockstep_issue.md) | 锁步加比较器，1 位和 17 位配置均在 XSim 展开时报端口宽度错误 | 参数组合支持范围；尚未运行功能输入 |  |
| 4 | [AXI GPIO 第二通道](../ip/axi_gpio/register_issue.md) | 3 组单通道配置首次在未启用的 `GPIO2_TRI` 读回失败；独立 VHDL 读回 `0xFFFFFFFF`，手册要求 0 | 厂商如何解释这处读回差异 |  |
| 5 | [AXI GPIO 方向切换](../ip/axi_gpio/direction_write_issue.md) | 独立 8 位 VHDL 复现输入方向写入后切回输出；另有 5 组双通道配置在相关写入序列失败 | “输入时写入无效”的含义；5 组是否同因 |  |
| 6 | [AXI INTC ISR](../ip/axi_intc/isr_write_issue.md) | 独立 VHDL 观察到 ISR 旧位丢失；整批自检有 12 组配置在 ISR 保留测试段失败 | 实测与手册写 0 不起作用的规定为何不同；12 组是否同因 |  |
| 7 | [AXI INTC ME](../ip/axi_intc/master_enable_issue.md) | 1 路硬件中断；待处理中断时清 ME，寄存器已关闭但 IRQ 仍为 1 | IRQ 撤销时序；与 ISR 写入分别排查 |  |
| 8 | [浮点乘法](../ip/floating_point/multiply_rounding_issue.md) | 双精度 `Low_Latency`；期望 1.0，实测约 0.5；速度优化模式对照通过 | 低延迟模式的影响范围；5 个样例暂归一个问题 |  |
| 9 | [FIR 全精度](../ip/fir_compiler/full_precision_issue.md) | 8 位输入、4 位系数；两组负系数 × 两种架构，共 4 组失败；`-128 × -8` 应为 +1024，实际 -1024 | 自动输出位宽规则；四组暂归一个问题 | :white_check_mark: |
| 10 | [Mailbox TLAST](../ip/mailbox/tlast_issue.md) | 32 位 AXI4-Stream，4 组深度/存储组合均出现 `TLAST=1` 变 0 | 此模式是否承诺传递 TLAST |  |
| 11 | [累加器](../ip/accumulator/ce_bypass_issue.md) | 8 位有符号输入、16 位输出；`CE=0、BYPASS=1` 时期望保持 1，实际变 0 | CE/BYPASS 优先级，可能是参考模型理解有误 |  |

INTC、浮点乘法和 FIR 的独立 VHDL 复现不依赖 Python 参考模型。
同一问题在多个位宽、延迟或种子下触发，只扩大影响范围，不增加 bug 数量。
本机复现也不能证明问题首次发现、尚未修复，或硬件实现必然有同样缺陷。

## 公开证据

`runs/` 和 `reports/` 不整体提交。2026.1 的运行报告、独立复现摘要和日志见
[问题观察证据](../../evidence/vivado_2026_1/observations/)；
478 组的报告与新差异输入输出见
[全量运行证据](../../evidence/vivado_2026_1/full_regression/)。

## 不计入的情况

- [AXI to LMB Bridge](../ip/axi_lmb_bridge/data_issue.md)：测试端没有把 Frequency 模式的读数据和读 UE 延后一拍。修正后，原两组及全部 5 组常用配置通过，固定请求对照也通过。
- [AXIS Protocol Checker](../ip/axis_protocol_checker/partial_issue.md)：TSTRB 缺省时等于 TKEEP，参考漏算了这个关系。独立 VHDL 对照符合该规则，修正参考后全部 6 组常用配置通过。
- Timer 捕获回绕脉冲的遗漏是 Python 参考模型错误，已修复。
- 大预算 AXI-Lite 仿真的超时常量越界是框架 VHDL 生成错误，已修复。
- 浮点定向输入的窄 USER 通道长期为零是框架覆盖缺口，已修正，见[标签说明](../ip/floating_point/user_patterns.md)。
- 人为故障注入用于检查 testbench，不能作为厂商 bug。
- [CORDIC 舍入差异](../ip/cordic/rounding_review.md)涉及内部精度，不能仅与精确数学结果不同就判错。
- [浮点下溢规则](../ip/floating_point/underflow_review.md)有手册正文与注释冲突，当前未计为实现缺陷。
- 不合法参数被 Vivado 拒绝、环境失败、日志误判，也不能直接计入。
- INTC 的部分写副作用、HIE 启用前的历史事件、ILR 非阈值高位编码仍需明确规范，暂不计入。

后续先缩减输入、保留正向对照，再核对规范、其他版本和官方记录。
未经用户决定，不自动提交厂商工单或公开声称已经确认新 bug。

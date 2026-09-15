# 待确认问题

截至 2026-09-15，以下异常有本机运行记录，但厂商确认数量仍为 0。
表中每行是一组排查线索，不是已确认的独立 bug 数量。

| 对象 | 已有证据 | 还需确认 |
| --- | --- | --- |
| [复数乘法器](../ip/complex_multiplier/latency_issue.md) | 手动长延迟时数值提前，独立 VHDL 可复现；较短延迟对照正常 | 其他版本、官方已知问题和受影响参数范围 |
| [旧版 xlconcat](../ip/xlconcat/port_128_issue.md) | 128 路非零输入输出零；直接编译附带模型也复现；127 路及新版对照正常 | 旧版已停止支持，是否有新的报告价值 |
| [TMR 投票器](../ip/tmr_voter/lockstep_issue.md) | 锁步加比较器时，厂商内部端口宽度不符，独立工程无法展开 | 参数组合支持范围、其他版本和官方记录；不是已证明的数值错误 |
| [AXI GPIO](../ip/axi_gpio/register_issue.md) | 方向切换和未启用寄存器读回与手册有差异，独立 VHDL 有记录 | 方向写入语义与版本说明；两种现象是否为独立原因 |
| [AXI INTC ISR](../ip/axi_intc/isr_write_issue.md) | ISR 写零清除旧位，写另一位覆盖旧位；预编译库与原始 HDL 均复现 | 是实现还是文档问题，是否已有官方说明；两种写入触发暂归一个问题 |
| [AXI INTC ME](../ip/axi_intc/master_enable_issue.md) | ME 清零后已有效的 IRQ 不撤销；纯硬件输入及原始 HDL 均复现，未写 ISR | 更多模式、版本、官方已知记录；与 ISR 暂分别排查，不是已确认数量 |
| [浮点乘法](../ip/floating_point/multiply_rounding_issue.md) | 双精度 Low_Latency 乘法应舍入为 1.0，实测约 0.5；独立 VHDL 两次复现，Speed_Optimized 和厂商 C 数值模型对照正常 | 其他版本、官方记录和影响范围；5 个差异样例暂归一个问题 |
| [FIR 全精度](../ip/fir_compiler/full_precision_issue.md) | 负系数与最小负输入得到正结果，实测符号翻转；两种架构独立 VHDL 复现，正系数对照正常 | 位宽规则、行为模型与文档的责任边界，其他版本和官方记录；两组系数暂归一个问题 |
| [累加器](../ip/accumulator/ce_bypass_issue.md) | CE/BYPASS 同时出现时有差异 | 控制优先级的规范解释，证据强度低于前几项 |

除 FIR 目前只有专用复现命令，其余条目均有常规框架配置。
INTC、浮点乘法和 FIR 的独立 VHDL 复现不依赖 Python 参考模型。
同一问题在多个位宽、延迟或种子下触发，只扩大影响范围，不增加 bug 数量。
本机复现也不能证明问题首次发现、尚未修复，或硬件实现必然有同样缺陷。

## 不计入的情况

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

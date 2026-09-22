# Vivado 2026.1 常用配置全量运行

2026-09-22 在 Vivado 2026.1 上执行：

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --all
```

本次覆盖 64 类 IP、478 组常用配置。只做行为仿真，不做综合或实现。
原始批次编号为 `2026-09-22_12-47-30_UTC+0800_4bca4f69`，
`run.json` 的状态为 `completed`，结果为 `FAILURES_OBSERVED`。
478 组创建 IP 都通过；475 组生成了 testbench；其中 436 组自检通过，
36 组仿真失败，3 组文件校验失败。`divider_u16_u8` 的官方 demo 另行通过。
原始报告共 1432 行；3 组因 testbench 生成失败而没有仿真行。

| 失败位置 | 配置数 | 目前判断 |
| --- | ---: | --- |
| 复数乘法 testbench 生成 | 2 | 2026.1 组合模式的 XCI 带 `aclk`；框架已适配，单独复测通过 |
| AXIS Protocol Checker testbench 生成 | 1 | 无 `TREADY` 时 XCI 将 `MAX_WAITS` 固定为 0；框架已适配，单独复测通过 |
| 累加器、复数乘法长延迟、TMR、GPIO、旧版 xlconcat | 14 | 与既有待确认现象同类，仍需核对规范或厂商模型 |
| CORDIC 平方根 | 5 | 精确数学参考与厂商内部精度存在差异，不能直接算 IP bug |
| 双精度浮点低延迟乘法、Mailbox TLAST、AXI INTC | 17 | 与此前 2026.1 独立复现的现象同类，不能按配置数计算 bug |
| AXI to LMB Bridge 文件校验 | 2 | `frequency_40` 和 `pause_64` 的数据及响应有差异，原因未定 |
| AXIS Protocol Checker 文件校验 | 1 | `axis_pc_128_partial` 的状态位比参考值多 bit 6，原因未定 |

修复两个框架适配点后，单独复测 `cmul_comb_pad11`、`cmul_comb_round`、
`axis_pc_no_ready_sidebands`，三组的创建、生成和仿真均通过。
复测编号为 `2026-09-22_16-09-47_UTC+0800_7e11e8e7`。
因此，按最近一次结果计算，478 组中有 439 组自检通过、39 组仍有失败；
这不是一次重新执行全部 478 组的“全绿”报告。

新出现的三条文件校验失败尚未有独立 VHDL 复现。
AXI to LMB Bridge 两组从第 3 条输出开始出现数据差异，第 19 条还出现响应差异。
Protocol Checker 的 `axis_pc_128_partial` 第 5、14、23 条输出中，
参考状态为 bit 3，实际还置了 bit 6。该配置没有启用 `TSTRB` 端口，
所以不能直接按当前参考表把 bit 6 解释成 `TSTRB` 变化。
需要核对状态位定义和激励，再决定是修 testbench、参考模型，还是继续调查 IP。
现在不计为确认 bug。

原始报告、复测报告和上述三组的输入输出、失败摘要在
[公开证据](../../evidence/vivado_2026_1/full_regression/)；
本机完整工程和日志在 `runs/batches/2026.1/<运行编号>/`、
`runs/logs/batches/2026.1/<运行编号>/`。
报告行数不是 bug 数；厂商确认的 bug 仍为 0。
大参数矩阵 9,667,722 组不在本次范围内，也没有自动展开多个种子或时序模式。

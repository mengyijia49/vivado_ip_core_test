# AXI INTC 接口探测

2026-09-15，Vivado 2025.2，`axi_intc:4.1` 修订 22。
本页记录接入前的独立探测。后续已加入[统一流水线和参数矩阵](selfcheck.md)，
以下历史编号和观察仍保留，不用新结果覆盖旧记录。

## 已生成的配置

编号 `2026-09-15_10-55-04_UTC+0800_b6742a4f` 的三组工程均能创建：
默认 1 路、4 路混合触发加 2 个软件中断、32 路电平触发且关闭可选寄存器。
工程、日志和报告分别位于 `runs/framework/intc_catalog/`、
`runs/logs/framework/intc_catalog/`、`reports/framework/intc_catalog/` 的编号目录下。

实测为 9 位地址、32 位数据的 AXI-Lite 接口，带 4 位 WSTRB，没有 AWPROT/ARPROT。
时钟为 `s_axi_aclk`，低有效复位为 `s_axi_aresetn`。
`intr` 为硬件中断路数宽的输入向量，`irq` 为标量输出。
普通模式没有 processor_clk、processor_rst、processor_ack 和 interrupt_address 顶层端口。
后续接入使用独立的中断状态模型，不沿用 GPIO 的中断翻转规则。

## 混合触发观察

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
VIVADO_INTEGRATION=1 PYTHONPATH=src python3 -m unittest discover \
  -s tests -p 'test_intc_probe.py' -v
```

编号 `2026-09-15_11-00-22_UTC+0800_9382f6b2`，配置为上升沿、高电平、下降沿、低电平各一路，
另加两个软件中断和 ILR。完整观察位于 `reports/framework/intc_probe/<编号>/summary.json`。
中断优先级、IAR 清除、持续有效电平重新置位、ILR 屏蔽 IRQ 的观察符合本次手工预期。
ILR 不改变 IPR 与 IVR 的读数，HIE 置位后再写零也不会清除。

禁用硬件输入时发生过的事件，在 HIE 开启后出现在 ISR 中。
增加切换后的独立读数后，确认它发生在再次写 ISR 之前，不能称为“软件仍能写硬件中断位”。
该启动边界仍需核对手册语义，不计作确认的缺陷。

WSTRB=0 至 14 的写入均返回 SLVERR，但 IER 仍更新为整字写入值；WSTRB=15 返回 OKAY。
手册没有明确这里的部分写和失败副作用，暂作观察，不沿用 Timer/GPIO 忽略 WSTRB 的参考。

本次探测末尾因规范差异返回 FAIL，不是创建或编译失败。
其中 ISR 写零及依次写不同位的问题，已缩成[无外部中断活动的独立复现](isr_write_issue.md)。

## 仓库检查

检查编号 `2026-09-15_11-09-17_UTC+0800_b664e991`：`py_compile` 通过，
完整测试 582 项，其中 413 项通过、169 项真实集成测试按环境开关跳过，耗时约 804 秒。
上述 INTC 真实复现另行执行，仍报告失败，不能用单元测试通过代替功能结论。
270 份运行源码、207 份测试文件、1316 份配置文件的前后哈希一致；
输入、日志和结果在对应的 `framework/intc_validation/<编号>/` 目录内。
默认流水线 `2026-09-15_11-09-18_UTC+0800_0b913fb3` 的 19 个阶段全部通过，
270 份源码和 508 个归档产物的哈希均已复核。

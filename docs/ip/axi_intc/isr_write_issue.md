# ISR 写入丢失已有中断位

2026-09-15，Vivado 2025.2，AXI INTC 4.1 修订 22，Artix-7。
状态：独立行为仿真可复现，尚未经过厂商确认，也未确认是否为已知问题。

## 最小复现

配置为 1 个硬件中断、2 个软件中断，关闭快速模式和 ILR。
外部中断始终为 0，所有写入均为对齐整字，WSTRB=15。
每次操作等待 64 个时钟。直接运行手写 VHDL，不使用 Python 数值模型或输入文件。

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
VIVADO_INTEGRATION=1 PYTHONPATH=src python3 -m unittest discover \
  -s tests -p 'test_isr_write_probe.py' -v
```

该命令分别使用预编译 IP 库和重新编译的原始 HDL，当前两个检查都会报告 FAIL。
不是故意注入错误的模型，也不是把失败当作通过；日志与读数会在断言前保存。
VHDL 见 [tb_isr_write_probe.vhd](../../../tests/fixtures/ip/axi_intc/tb_isr_write_probe.vhd)。

[PG099 第 15 至 16 页](https://docs.amd.com/v/u/en-US/pg099-axi-intc)
规定 ISR 写入的 1 置位，0 不改变对应状态。因此依次置不同位应保留之前的位。

| 条件 | 操作 | 手册推导的 ISR | 实测 ISR |
| --- | --- | --- | --- |
| HIE=0 | 写 1，再写 0 | 1 | 0 |
| HIE=0 | 写 1，再写 2 | 3 | 2 |
| HIE=1 | 写 2，再写 0 | 2 | 0 |
| HIE=1 | 写 2，再写 4 | 6 | 4 |

HIE=1 的检查只写合法的软件中断位，不尝试修改硬件中断位。
写零时 IRQ 也从 1 变成 0。复位、首次置位、MER 读回和 IAR 确认清除共 10 项对照正常。
四个差异暂归为同一个 ISR 写入问题，不能算作四个独立 bug。

## 对照记录

| 运行 | 编号 | 结果 |
| --- | --- | --- |
| 首次隔离 | 2026-09-15_11-05-17_UTC+0800_0d434122 | 四项差异 |
| 直接编译附带 HDL | 2026-09-15_11-07-35_UTC+0800_50b362d1 | 相同四项差异 |
| 预编译库重复检查 | 2026-09-15_11-07-58_UTC+0800_54e17d14 | 相同四项差异 |

完整工程和快照在 `runs/framework/isr_write_probe/<编号>/axi_intc/`，
日志在对应的 `runs/logs/framework/isr_write_probe/`，
参数、原始读数、期望值及哈希在 `reports/framework/isr_write_probe/<编号>/summary.json`。
后两批的源码、脚本、testbench 和 XCI 哈希均已复核，14 项观察逐项一致。
纯源工程的 `xvhdl.log` 和 `xsim.ini` 确认 INTC、AXI-Lite IPIF 都使用本次编译的本地库。

附带 HDL 的 ISR 更新使用写入值直接赋值，与实测一致；没有修改厂商文件。
本机 change log 未找到该语义的修正说明，但这不能证明不存在官方已知问题记录。

## 影响与限制

官方驱动的 [XIntc_TriggerSwIntr](https://github.com/Xilinx/embeddedsw/blob/bb2b3f9fe65a74d458ab21f1006cb52820981520/XilinxProcessorIPLib/drivers/intc/src/xintc.c)
也是向 ISR 写入一个位掩码，没有先读回已有状态。
据此推测，在前一个软件中断尚未确认时触发另一个，可能丢失前者。
这里只核对了驱动源码，没有运行 CPU 软件或证明板上存在同样现象。
源码检查记录为 `2026-09-15_11-10-40_UTC+0800_4c47298b`，位于 `reports/framework/intc_source_review/`。

下一步核查其他 Vivado 版本及官方说明，确认应修改 IP 实现还是手册。
本机当前只有 Vivado 2025.2，尚未做跨版本对照。
不把“本机可复现”写成“新发现且厂商确认”，也不通过改期望值来消除失败。
HIE 切换和非整字写的其他观察见[接口探测](interface_probe.md)，不混入本项复现。

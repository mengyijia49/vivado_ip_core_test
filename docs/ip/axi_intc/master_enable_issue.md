# AXI INTC 清除 ME 后 IRQ 仍有效

2026-09-15，Vivado 2025.2，`axi_intc:4.1` 修订 22。
这是待确认的规范与实现差异，尚未获得厂商确认，也未检查其他 Vivado 版本。

## 现象

[PG099 v4.1 第 23 页](https://docs.amd.com/v/u/en-US/pg099-axi-intc)说明，
MER 的 ME 位为零时应屏蔽 IRQ 输出。
本机实测：如果 IRQ 已经有效，再清零 ME，MER 能正确读回，但 IRQ 仍保持有效。
先清 IER 或确认中断后，IRQ 可以恢复无效。

独立复现只使用一路上升沿硬件输入，关闭软件中断、Fast 和 ILR。
全程不写 ISR，因而不依赖另一项 ISR 覆盖旧位的问题。
读写均使用完整字和 AXI-Lite 握手，每次操作后等待 64 个时钟。

| 操作 | 读回 | 期望 IRQ | 实测 IRQ |
| --- | --- | ---: | ---: |
| IER=1，MER=3，触发并释放 intr(0) | ISR=1 | 1 | 1 |
| MER=0 | MER=2，HIE 保持 | 0 | 1 |
| 再读状态 | ISR=1 | 0 | 1 |
| IER=0 | IER=0 | 0 | 0 |
| IER=1，ME 仍为零 | ISR=1 | 0 | 0 |
| MER=1 | MER=3 | 1 | 1 |

共 13 项观察，11 项正向对照符合预期，2 项记录同一个 IRQ 未关闭现象。
对照另包括确认中断、ME 关闭时的新输入事件、重新启用和复位。
两条差异不是两个 bug。

## 复现

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
VIVADO_INTEGRATION=1 PYTHONPATH=src python3 -m unittest discover \
  -s tests -p 'test_master_enable_probe.py' -v
```

该命令执行预编译库和原始 HDL 两种路径，当前都应报告规范检查失败。
最小 testbench 是 `tests/fixtures/ip/axi_intc/tb_master_enable_probe.vhd`，
没有调用 Python 参考模型。

首次两条记录：

- 预编译库：`2026-09-15_11-41-11_UTC+0800_7f4ee548`。
- 直接编译原始 HDL：`2026-09-15_11-41-29_UTC+0800_8f3d1c77`。

13 项观察完全一致。产物、日志、摘要分别位于 `runs/framework/master_enable_probe/`、
`runs/logs/framework/master_enable_probe/`、`reports/framework/master_enable_probe/` 的编号目录。
摘要保存配置、修订号、期望与实测值，以及 testbench、XCI 和源码的哈希。
原始 HDL 对照的 xvhdl.log 和 xsim.ini 确认 IPIF、INTC 被编译到工程本地库。
可提交的小证据包：[evidence/axi_intc/master_enable](../../../evidence/axi_intc/master_enable/README.md)。

## 判断和疑点

随 IP 生成的未修改 HDL 中，`IRQ_LEVEL_ON_AXI_P` 在无挂起中断时撤销 IRQ，
在有挂起中断且 ME=1 时置位，却没有在仍挂起且 ME=0 时撤销的分支。
这能解释实测保持现象，但 RTL 只用于排查原因，不作为期望值依据。

官方驱动的 [XIntc_Stop](https://github.com/Xilinx/embeddedsw/blob/bb2b3f9fe65a74d458ab21f1006cb52820981520/XilinxProcessorIPLib/drivers/intc/src/xintc.c)
通过向 MER 写零停止控制器，与这次触发操作一致。
没有实际执行处理器软件，不能据此宣称某个应用已发生故障。

下一步核对官方已知问题、其他版本和更多输出模式。
本机搜索未找到对应说明不代表首次发现；行为仿真结果也不等于已验证板级影响。

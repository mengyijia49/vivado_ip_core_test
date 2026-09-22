# Mailbox 自检

## 已检查的内容

当前接入 `mailbox:2.1` 的双 AXI4-Lite 和双 AXI4-Stream 同步时钟模式。两种模式
都检查两条方向相反的 FIFO，不把不同接口的配置和 testbench 混在一个文件里。

每组测试还会执行以下操作：

- 把发送 FIFO 写满，再多写一次，检查满错误和 AXI 写响应。
- 从空的接收 FIFO 读取，检查空错误和 AXI 读响应。
- 读取错误寄存器两次，确认错误在第一次读取后清除。
- 分别清除发送 FIFO 和接收 FIFO，检查状态变化。
- 设置发送和接收阈值，检查中断状态、使能寄存器和中断输出。
- 暂时不接收 AXI 写响应和读数据，检查 IP 是否保持响应。
- 在运行中复位两个端口，检查 FIFO、错误和中断状态是否回到初始值。

Python 参考模型分别保存两个方向的 FIFO，计算满、空、错误和状态位。VHDL testbench
负责执行 AXI 事务并写出九项检查结果，Python 再比较结果文件。

AXI4-Stream testbench 还会检查：

- S0 输入是否只从 M1 输出，S1 输入是否只从 M0 输出。
- 数据顺序和 `TLAST` 是否保持不变。
- FIFO 写满后 `TREADY` 是否拉低，是否拒绝额外输入。
- `TREADY` 拉低期间，`TVALID`、`TDATA` 和 `TLAST` 是否保持。
- 两个方向同时传输并分别施加回压时，是否漏发、重复或串路。
- FIFO 中仍有数据时复位，旧数据是否被清除。

## 参数范围

常用回归有 8 组：4 组 AXI4-Lite 和 4 组 AXI4-Stream。可选大矩阵包含 80 组
AXI4-Lite 配置和 20 组同步 AXI4-Stream 配置，共 100 组。

运行常用配置：

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type mailbox
```

只运行大矩阵中的前几组：

```bash
python3 scripts/run_all.py --config configs/ip/mailbox/extended.json --limit 4
```

## 已知限制

当前没有检查 AXI4-Stream 异步时钟、不同同步级数和 UltraRAM。
阈值测试只检查一次上升和清除过程，不穷举所有阈值与 FIFO 占用量的状态序列。
2026.1 全量运行中的 AXI4-Lite 四组配置、12 个阶段全部通过。
AXI4-Stream 的分布式 RAM 和块 RAM 配置完成了数据检查，但因
`TLAST` 丢失而失败，见 [TLAST 待确认问题](tlast_issue.md)。

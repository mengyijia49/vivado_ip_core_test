# AXI4-Stream FIFO 自检

## 怎么运行

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type axi_fifo_mm_s
```

常用回归有 4 组。大矩阵有 1620 组，可单独查看和分批运行：

```bash
python3 scripts/run_all.py --config configs/ip/axi_fifo_mm_s/extended.json --list-cases
python3 scripts/run_all.py --config configs/ip/axi_fifo_mm_s/extended.json --limit 4
```

## 怎么检查

Python 模型按 PG080 的寄存器顺序生成 AXI4-Lite 操作。测试先把数据写入发送 FIFO，
再写长度寄存器启动一个包。IP 的发送流直接接到接收流，接收端随后通过长度、目的字段
和数据寄存器读回。模型独立保存每个包的内容、长度和目的字段，并逐项比较读回结果。

测试会定期拉低流接口的 ready，检查 valid 为高而 ready 为低时，发送数据、包尾、
TKEEP 和 TDEST 是否保持。启用 TKEEP 时测试 1、2、3 字节尾包；未启用 TKEEP 时只发
4 字节对齐的包，因为接口不能表示一个数据拍里哪些字节无效。

还会检查发送空位、接收占用、完成中断、正确和错误的 FIFO 复位键、复位输出以及
AXI-Lite 读写响应。阈值和 ECC 中断位未启用，报告中明确屏蔽这些位，不拿未知状态评分。

## 参数

- `tx_depth`、`rx_depth`：发送和接收 FIFO 深度，可取 512 至 131072 的规定二次幂。
- `has_keep`：是否带 TKEEP，决定是否能表示最后一个数据拍的部分有效字节。
- `destination_width`：TDEST 位宽，0 表示不使用，1 至 4 表示启用并检查读回。
- `use_xpm`：选择 XPM 或原有 FIFO 实现。

## 当前范围

当前只测 32 位数据、AXI4-Lite 控制、store-and-forward 和同步时钟。尚未接入完整 AXI4、
cut-through、ECC、发送控制流、TID、TUSER、TSTRB 和异步时钟。大矩阵只完成参数格式
校验，没有全部运行 Vivado。

2026.1 全量运行中的 4 组配置、12 个阶段全部通过，
见[运行记录](../../experiments/vivado_2026_full_regression.md)。

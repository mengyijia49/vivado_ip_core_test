# 截取工具自检

对象是旧版 `xlslice:1.0`，不是 Inline HDL 的 `ilslice`。
Vivado 2025.2 的日志已提示迁移，当前保留旧版作为独立测试对象。

输入 `Din` 宽度为 `input_width`，输出 `Dout` 取 `high_bit` 到 `low_bit`，
两个端点都包含。没有时钟、复位或握手，单比特输出仍是向量。
Python 用整数除法和取模求期望值，与 [PB042 的位截取定义](https://docs.amd.com/v/u/en-US/pb042-xilinx-com-ip-xlslice)对应。

本机 Catalog 允许输入 2 至 4096 位，但截取下标仅为 0 至 255。
还需满足 `0 <= low_bit <= high_bit < input_width`。输入很宽不代表可以选第 4095 位。

测试包括各位的不同变化模式、选中位的独热及其反码、紧邻选区的位和输入最高位。
未选位发生变化时，输出仍须保持正确。采样只检查稳定后的组合结果，不检查毛刺。

```bash
python3 scripts/run_all.py --ip-type xlslice
python3 scripts/run_all.py --config configs/ip/xlslice/extended.json --list-cases
```

常用回归 6 组，大矩阵 61580 组。矩阵包含小宽度的全部区间、
33/65/129/256 位输入的全部合法区间、宽输入上的边界区间，以及输入宽度扫描。
参数区间遍历和输入值穷举是两回事：只有输入不超过 8 位时才穷举输入值。
代表配置的结果见[连接工具验收](../../experiments/utility_acceptance.md)。

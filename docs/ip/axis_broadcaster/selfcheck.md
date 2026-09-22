# AXI-Stream 广播器

对应 `xilinx.com:ip:axis_broadcaster:1.1`。只做行为仿真。

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type axis_broadcaster
```

## 测什么

一拍输入发给 2 至 16 条支路。各支路可以在不同周期接收，同一拍不能漏发或重复发。
输入会保持到上游握手完成；检查器允许某些输出支路先于上游握手接收。
输入尚未提供时出现输出、回压时数据或有效信号改变、未知值和输出不匹配，都会失败。
缺少支路输出会由计数或超时检查捕获。

每条支路有独立随机就绪序列，并安排“只有这一条暂停”和“只有这一条就绪”的时段。
事件和统计会记录实际发生的握手，不能把安排过某种时序当作已经覆盖。
逐位单 1、单 0 前缀后接策略生成的数值样本；前缀不计入随机唯一值数量。

数据映射可选原样复制、按支路号轮转字节、奇数支路反转字节、分段拆分、支路常量。
用户字段可选复制、按支路号轮转位、分段拆分、支路常量。
宽度增加时高位补零，减少时取映射结果的低位；拆分按支路号从输入低位向高位取段。
Python 用数值运算计算答案，不从生成的 Tcl 映射字符串或 DUT 输出取得答案。

映射依据 [PG085 支路说明](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/Stream-Splitting-Options)。
实际 XCI 的支路数、映射参数、端口集合和位宽必须与配置相符。

## 参数文件

常用配置 10 组，大矩阵 62550 组，均位于 `configs/ip/axis_broadcaster/`。

| `matrices/` 子文件 | 参数组数 |
| --- | ---: |
| `data_replicate.json` | 6615 |
| `data_rotate_bytes.json` | 6615 |
| `data_reverse_alternate.json` | 6615 |
| `data_constant_tag.json` | 6615 |
| `split.json` | 810 |
| `sideband_only.json` | 18000 |
| `full_sideband.json` | 17280 |

```bash
python3 scripts/run_all.py --config configs/ip/axis_broadcaster/extended.json --list-cases
python3 scripts/run_all.py --config configs/ip/axis_broadcaster/extended.json --limit 3
```

数据宽度最高 512 字节，TUSER 最高 4096 位，TID/TDEST 最高 32 位。
宽字段乘以多条支路后，输入、输出和日志可能很大，先选择少量配置检查磁盘占用。
大矩阵只做参数与预算校验，不表示每组都已运行 Vivado。

## 文件含义

物理输出端口的低位属于 M00。输入和参考文件按 manifest 中记录的字段顺序打包。
`actual_output.txt` 一行对应一拍输入的完整广播，文件中 M00 放最左侧，随后是 M01 等。
每个片段都在对应支路实际握手时采样，不要求各支路同时握手。
发生数值错误时，最后一行可以包含尚未接收支路的 `X`，原始事件仍保留。

`protocol_events.txt` 记录时钟周期、支路号、该支路的接收序号、VALID/READY 和实际字段。
`protocol_summary.txt` 记录每条支路接收数、回压周期数和先于上游完成的握手数。
报告中的 `output_count` 是完整广播数，`checked_output_transfers` 是各支路期望接收数之和。
包尾数也按全部支路求和。`accepted_input.txt` 从实际驱动信号采样，并与输入文件再比较。

## 当前限制

这是针对组合数据通路广播器的检查器，不用于带独立深缓冲的多播路由器。
当前启用 TREADY、不启用 ACLKEN，仅测试启动复位；运行中复位尚未接入。
TDATA/TUSER 要求两侧同时存在或同时关闭，不覆盖单侧增加、删除信号。
KEEP/STRB 目前全为 1，启用它们时要求两侧字节宽度相同。
测试未覆盖稀疏字节、自定义跨字段表达式，以及关闭 TREADY 的模式。

# AXI-Stream 子集转换器

对应 `xilinx.com:ip:axis_subset_converter:1.1`。测试范围只限行为仿真。
一拍输入对应一拍映射后的输出，不按位宽转换器的字节序列规则比较。

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type axis_subset_converter
```

## 参数与矩阵

常用配置 13 组，包括位/字节反转、轮转、重复低字节、跨字段映射、常量、包尾计数，
以及只有侧带、没有 TDATA 的接口。
大矩阵有 16425 组，入口为 `configs/ip/axis_subset_converter/extended.json`：

| 子文件，位于 `matrices/` | 参数组数 | 内容 |
| --- | ---: | --- |
| `data_mapping.json` | 2205 | 五种数据映射，21 种输入/输出字节宽度 |
| `packetization.json` | 2570 | 10 种输入宽度，包尾周期 0 到 256 |
| `sideband_mapping.json` | 5400 | 独立侧带宽度、数据/用户字段交换、补位和截取 |
| `sideband_only.json` | 6250 | 无 TDATA，TUSER 从 1 到 4096 位，10 种包尾周期 |

```bash
python3 scripts/run_all.py --config configs/ip/axis_subset_converter/extended.json --list-cases
python3 scripts/run_all.py --config configs/ip/axis_subset_converter/extended.json --limit 3
```

`input_*` 和 `output_*` 分别描述两侧接口。`mapping` 选择预置映射，
`last_period` 设置自动包尾周期；非零值要求没有输入 TLAST、启用输出 TLAST。
可选 `remap` 用字段名覆盖具体映射，例如：

```json
{"remap": {"tdata": "8'b10100101,tuser[7:0],tdata[7:0]", "tuser": "tdata[7:0]"}}
```

此例要求输入 TDATA/TUSER 至少 8 位，输出 TDATA 为 24 位、TUSER 为 8 位。
规则依据 [PG085 映射说明](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/Extra-Settings)：
右侧元素放低位，只接受二进制常量和已有输入的切片，不执行表达式中的代码。
没有输入 TDATA 时，工具只接受单个常量作为输出 TDATA 映射。

## 自检方法

预置模式用 Python 位运算计算期望值，不读取生成的映射表达式作为答案。
自定义模式由独立解析器求值，检查切片范围、常量位数和总宽度。
XCI 必须与请求的参数、映射字符串、端口集合和位宽一致。
Vivado 分段保存的长字符串按原顺序连接后比较，原始 XCI 保持不变。

输入前缀逐位发送单 1 和单 0，随后保留策略生成的数值样本。
自动包尾至少跨越两次计数回绕；前缀和补充拍不计入随机样本的唯一值数量。
比较只在握手时进行，包尾计数也只按成功传输推进。
同时检查回压保持、未知值、多余/丢失输出和实际接收的输入文件。
文件位置沿用[公共流接口记录](../../protocols/axis_stream.md)。

## 尚未覆盖

目前输入 KEEP/STRB 全为 1，不测试稀疏字节；每侧必须有至少一个有效载荷信号。
两侧 TREADY 均启用，不测试无输入 TREADY 时丢拍的模式。
删除输入 TKEEP 会增加 `sparse_tkeep_removed` 告警端口，目前会提前拒绝这种配置。
这些告警的定义见 [PG085 接口说明](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/Slave-Interface-Signals)。
ACLKEN、运行中复位及单侧复位尚未接入。大矩阵只做了参数检查，未全部仿真。

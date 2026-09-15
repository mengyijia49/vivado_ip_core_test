# 原生 FIFO 自检

`fifo_generator` 对应 `fifo_generator:13.2`，与 `axis_data_fifo` 分开维护。

```bash
python3 scripts/run_all.py --ip-type fifo_generator
python3 scripts/run_all.py --config configs/ip/fifo_generator/extended.json --list-cases
```

## 当前检查

使用同一时钟和同步复位，存储类型可选 Block RAM 或 Distributed RAM。
`read_mode` 可选 `standard` 或 `fwft`；旧配置没有该字段时仍使用标准读模式。
数据宽度 1 至 1024 位，深度为 16 至 131072 的二次幂。

Python 用队列保存已接受但尚未读出的数据，逐周期检查：

- 输出数据顺序和数值。
- full、empty、almost_full、almost_empty。
- valid、wr_ack、overflow、underflow，以及四个握手标志的高低有效极性。
- 写满、读空、同时读写、拒绝非法读写、指针回绕、非空时复位和复位后恢复。

定向前缀至少填满和读空两轮，随机阶段后再排空。
间隔周期关闭读写，不跳过状态检查。没有有效数据时不比较 dout，
但其余标志仍比较；复位周期另外检查 dout 的配置复位值。

依据 [PG057](https://docs.amd.com/v/u/en-US/pg057-fifo-generator)：
读写是否接受由时钟沿前的满空状态决定，满时同时读写不接受新写入，空时不直通。
同步复位时 underflow、overflow 仍取决于请求及相应状态，不能一律按零比较。

## FWFT 检查

FWFT 不需要先读才能看到首字。写入空 FIFO 后，首字经过两个额外时钟出现在输出，
同时 empty 撤销、valid 有效。rd_en 表示消费当前输出，停读时数据必须保持。
这些规则来自 [PG057 的读模式说明和延迟表 3-15 至 3-18](https://docs.amd.com/api/khub/documents/Ds0JjAYlvIFpRMxJMOrbRw/content)。

独立模型位于 `fwft.py`，用队列记录数据和写入周期，不读取 DUT 输出计算期望值。
容量为配置深度加二；almost_empty 对写入延后一拍，empty 延后两拍，
读操作对标志不另加延迟。八个状态和握手标志始终比较，没有给标志加掩码。

除两轮满空和回绕外，定向序列还包含：

- 空 FIFO 写入后的 0 至 4 拍间隔、提前读、首字出现和停读保持。
- 全部 1024 种连续五拍读写控制组合，每种从空状态开始，随后排空。
- 首字到达前后复位、满时同时复位及读写。

这不是全部 FIFO 历史的穷举，也没有穷举五拍内的所有数据值。
另有不调用 Python 模型的固定输入输出检查，以及错数、错标志、未知位等替身测试。

```bash
python3 scripts/run_all.py --config configs/ip/fifo_generator/regression/fwft.json
```

## 配置和限制

常用回归 24 组，大矩阵 181392 组。原有标准读 1152 组、FWFT 18432 组继续保留；
计数和阈值新增 161808 组，覆盖全部可用计数位宽、小深度下的阈值组合及大深度边界。
配置按读模式和存储类型分文件，入口仍为本目录的 `regression.json`、`extended.json`。
大矩阵只做配置检查和代表性实测，不能把配置数当成已完成的仿真次数。
报告中的 reference_sequence_events 是参考序列的事件计数，不是 DUT 内部覆盖率。

可选参数 `data_count_width`、`prog_full_assert`、`prog_full_negate`、`prog_empty_assert`、
`prog_empty_negate` 用于计数和常量阈值，省略时不增加端口。
具体含义和范围见[计数与阈值](status_protocol.md)。

尚未接入独立时钟、异宽端口、阈值输入端口、ECC 和内建 FIFO 原语。
实测编号和检查器结果见[FWFT 接入检查](../../experiments/fifo_fwft_acceptance.md)
和[计数及阈值接入检查](../../experiments/fifo_status_acceptance.md)。

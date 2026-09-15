# AXI-Stream 时钟转换器

IP：`xilinx.com:ip:axis_clock_converter:1.1`。

```bash
python3 scripts/run_all.py --ip-type axis_clock_converter
```

当前接入异步模式，输入、输出时钟周期分别为 10 ns、14 ns。
数据宽度为 1 至 64 字节，同步级数为 2 至 8；可选 LAST、KEEP、STRB、ID、DEST、USER。
两个复位端口一起复位，不开启时钟使能转换。

Python 参考模型保留事务原值与顺序，testbench 按各自时钟域的握手检查，
不把跨时钟延迟写死。异步延迟的说明见
[PG085](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/Performance)。

这仍是数字行为仿真，不是 CDC 结构检查或亚稳态验证。
同步整数比例模式、单侧复位、运行中改频尚未接入。
其余规则见 [流接口自检](../../protocols/axis_stream.md)，配置在 `configs/ip/axis_clock_converter/`。

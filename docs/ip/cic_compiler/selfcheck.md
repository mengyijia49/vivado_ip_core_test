# CIC Compiler 自检

`cic_compiler` 对应 `cic_compiler:4.0`。当前测试固定倍率、单通道、全精度输出的
抽取器和插值器。

```bash
python3 scripts/run_all.py --ip-type cic_compiler
python3 scripts/run_all.py --config configs/ip/cic_compiler/extended.json --list-cases
```

## 检查方法

Python 参考模型用整数实现级联积分器和梳状滤波器。抽取模式每隔指定输入数取一次结果；
插值模式在相邻输入之间补零，再经过积分器。模型根据倍率、级数和差分延迟计算全精度位宽，
最后按 AXI4-Stream 的字节宽度做符号扩展。

输入包含冲激、阶跃、正负交替、最大正数、最小负数和生成数据。testbench 检查每个有效
输出的数值和顺序，也检查输出数量。接收端停止时，`TVALID` 和 `TDATA` 必须保持。
抽取模式还检查每个输出出现前已经接收了足够的输入；插值模式检查一个输入对应的全部输出。

接口和计算顺序依据 [PG140 控制时序](https://docs.amd.com/r/en-US/2026.1/pg140-cic-compiler/Control-Signals-and-Timing)、
[抽取器说明](https://docs.amd.com/r/en-US/pg140-cic-compiler/CIC-Decimator)和
[插值器说明](https://docs.amd.com/r/en-US/2026.1/pg140-cic-compiler/CIC-Interpolator)。

## 配置范围

常用配置有 4 组，覆盖抽取和插值、8/16 位输入、2/3/4 级、1/2 拍差分延迟，
倍率为 4、5 或 8。大矩阵有 256 组，组合两种滤波方向、4 种输入位宽、4 种级数、
2 种差分延迟和 4 种倍率。大矩阵只完成参数校验，不会默认全部运行。

2026-09-22 使用 Vivado 2026.1 运行四组常用配置，12 个阶段均通过。
这只说明本批输入没有发现差异，见[全量报告](../../experiments/vivado_2026_full_regression.md)。

目前没有测试可编程倍率、多通道、截位输出、`ACLKEN` 和运行中复位。测试只覆盖行为仿真，
不检查实现后的资源、最高频率或时序。

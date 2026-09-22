# FIR Compiler 自检

`fir_compiler` 对应 `fir_compiler:7.2`。当前测试单速率、固定整数系数和全精度输出。

```bash
python3 scripts/run_all.py --ip-type fir_compiler
python3 scripts/run_all.py --config configs/ip/fir_compiler/extended.json --list-cases
```

## 检查方法

Python 保存已经被 IP 接收的输入。每收到一个新输入，就把它放到历史序列最前面，
再按配置中的系数逐项相乘并求和。历史开始时全为零。期望值不读取 Vivado 输出，
也不调用厂商 C 模型。

testbench 检查 AXI-Stream 的 `TVALID`、`TREADY` 和 `TDATA`。启用 `TLAST` 或
`TUSER` 时也逐拍比较这些信号。接收端会主动施加回压，并检查 IP 在等待期间是否保持输出。

常用配置有 3 组，分别覆盖正系数 Systolic、正负混合系数 Transpose，以及 16 位数据和侧带。
大矩阵有 96 组，组合 8、9、16 位数据，四组系数，两种架构和侧带开关。

## 当前范围

目前没有测试抽取、插值、多通道、系数重载、分数系数和截断输出。大矩阵只完成配置校验，
没有全部运行。三组常用配置已在 Vivado 2026.1 完成行为仿真并通过自检，
见[全量报告](../../experiments/vivado_2026_full_regression.md)。
接入过程中曾出现 XSim 快照间歇性启动异常，原样重跑后消失，没有把它计作 FIR 缺陷。

全精度负系数边界已有[独立复现记录](full_precision_issue.md)。常规流水线保留 Python 卷积参考，
独立复现继续保留写死的 VHDL 期望值，两者用途不同。

# I2S Transmitter 自检

## 检查内容

测试对象是 `i2s_transmitter:1.0` 的主模式。Python 生成各声道的有符号边界值、
固定图案和随机样本，并按 IP 的 AXI4-Stream 音频格式写入 `TDATA` 和 `TID`。
testbench 通过 AXI-Lite 设置串行时钟分频并启动发送，然后按握手送入样本。

testbench 在 `sclk_out` 上采样每条 `sdata_*_out`，按 `lrclk_out` 分开左右声道，
重新组成样本并写入 `actual_output.txt`。框架把它与 Python 生成的
`expected_output.txt` 逐项比较。输入样本带有 192 帧重复的 AES3 前导码和状态位，
用于经过 FIFO 预装后继续提供完整的音频帧。

原生 LR 槽宽下，LR 切换所在的时钟沿仍属于前一个声道的最低位；32 位 LR 槽宽下，
只取前 16 或 24 个数据位，忽略槽尾填充位。testbench 先等待固定同步样本，
同步后才记录本次预算内的结果。

## 参数范围

常用回归有 5 组配置，覆盖 16/24 位样本、2/4/6/8 声道、原生或 32 位 LR 槽、
64 至 1024 深度的 FIFO，以及 1、2、4、8、15 倍串行时钟分频。
可选大矩阵有 1200 组配置。

## 运行方法

运行五组常用配置：

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type i2s_transmitter
```

只运行一个配置：

```bash
python3 scripts/run_all.py --ip-type i2s_transmitter --case i2stx_16_quad_32lr_d2
```

列出或抽取大矩阵：

```bash
python3 scripts/run_all.py --config configs/extended_discovery.json \
  --ip-type i2s_transmitter --list-cases
python3 scripts/run_all.py --config configs/extended_discovery.json \
  --ip-type i2s_transmitter --limit 3
```

## 已运行结果

2026.1 全量运行中的 5 组常用配置、15 个阶段全部通过，
见[运行记录](../../experiments/vivado_2026_full_regression.md)。

这些结果没有发现新的 IP 功能异常。调试中发现并修正的是 testbench 对 LR 切换边沿
和槽尾填充位的处理，不是 IP 缺陷。

## 尚未覆盖

当前没有检查从模式、中断、FIFO 计数、运行中复位、更多主时钟频率和全部 1200 组参数。
代表配置通过不能说明所有参数都通过，也不能说明 IP 没有其他缺陷。

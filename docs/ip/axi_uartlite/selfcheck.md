# AXI UART Lite 自检

## 运行方法

运行四组常用配置：

```bash
python3 scripts/run_all.py --ip-type axi_uartlite
```

查看 84 组扩展参数，或选取其中一部分运行：

```bash
python3 scripts/run_all.py --config configs/ip/axi_uartlite/extended.json --list-cases
python3 scripts/run_all.py --config configs/ip/axi_uartlite/extended.json --limit 4
```

## 检查内容

testbench 把 `tx` 接回 `rx`。Python 参考模型独立维护 16 字节接收 FIFO，
通过 AXI-Lite 写发送寄存器，再按顺序读取接收到的字符。输入包括 5、6、7、8 位字符，
无校验、偶校验和奇校验，以及 9600 至 230400 的七种可用波特率。

定向序列会填满接收 FIFO，再发送第 17 个字符检查溢出状态。它还检查空 FIFO 读取的
`SLVERR`、状态寄存器、FIFO 清除、复位和全部 16 种写选通值。手册规定该 IP 忽略写选通，
所以不同 `WSTRB` 应得到相同结果。每次发送后会等待一个完整串行帧，再开始下一次总线操作。

2026.1 全量运行中的四组配置、12 个阶段全部通过，
见[运行记录](../../experiments/vivado_2026_full_regression.md)。

## 当前限制

当前使用内部串行回接，没有单独注入错误起始位、停止位或校验位，因此不检查接收错误识别。
每次发送都会等待完成，尚未把发送 FIFO 写满，也未检查写满后的 `SLVERR`。
中断使能状态会检查，但中断脉冲可能发生在两次检查之间，目前不严格比较脉冲次数。
84 组扩展参数已通过静态校验，只有四组代表配置实际运行过 Vivado。

测试只运行行为仿真，不包含综合、实现、板级串口或电气时序。

接口和寄存器语义参考 [AXI UART Lite Product Guide PG142](https://docs.amd.com/v/u/en-US/pg142-axi-uartlite)。

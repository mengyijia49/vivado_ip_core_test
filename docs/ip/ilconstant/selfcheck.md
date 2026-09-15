# Inline Constant 自检

对象是 `xilinx.com:inline_hdl:ilconstant:1.0`。只有 dout 输出，没有输入、时钟、复位或握手。
每次创建确定一个常量，之后观察 64 次，检查数值、未知位和意外变化。
报告把这 64 次记为输出观察，不记为 64 个输入事务。

## 参数和检查

`width` 为 1 至 4096；`value` 必须是字符串，数值不能超出宽度。
支持十进制、`b` 开头的二进制、前导 `0` 的八进制、`0x` 或 `0X` 开头的十六进制。
例如 `"85"`、`"b1010101"`、`"0125"` 和 `"0x55"` 表示同一个值。

Python 独立解析常量。传给 Vivado 的原始写法和实际 `.bd` 参数都会保存并核对，
不从生成的 HDL 或实际输出反推期望值。最高位和超过机器整数宽度的值也参与比较。

常用回归有 8 组，包含四种写法和 4096 位值。
大矩阵有 16861 组不同数值参数：每种宽度的零、一、最高位置一、全一，
以及部分边界宽度的交替位、首尾位和字长边界值。
相同宽度、相同数值只计一组，不靠改变常量写法增加数量。

## 运行

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type ilconstant
python3 scripts/run_all.py --all --case ilconstant_decimal4096
python3 scripts/run_all.py --config configs/ip/ilconstant/extended.json --list-cases
```

范围依据为本机 Vivado 2025.2 的 `data/rsb/iprepos/ilconstant_v1_0/component.xml`；
不同写法另有实际仿真检查。创建使用 Inline HDL，配置在 `.bd` 中，不是独立 XCI。
Inline HDL 说明见 [UG994](https://docs.amd.com/r/en-US/ug994-vivado-ip-subsystems/Inline-HDL)。

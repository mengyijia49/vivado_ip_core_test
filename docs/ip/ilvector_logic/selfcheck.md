# Inline 向量逻辑自检

对象是 `xilinx.com:inline_hdl:ilvector_logic:1.0`，与旧版 `util_vector_logic` 分开测试。
`operation` 选择 `and`、`or`、`xor` 或 `not`，`width` 指定输入输出宽度。
Op1、Op2 为输入，Res 为输出，全部是向量；取反模式没有 Op2。
没有时钟、复位或握手。

Python 按位计算期望值，小位宽另用完整真值表检查参考模型。
仿真输入包括各端口边界、相同和互反的操作数、随机值和逐位标识序列。
与运算要让另一个输入全一，或运算要让另一个输入全零，才能看出单个输入位是否接错。
定向序列包含这些组合，不只测两路同时变化。

## 参数范围

框架目前接受 1 至 65536 位。这是本轮接入的范围，不是厂商声明的最大值。
安装包 XML 没有给出明确上限，65536 位已实际创建。
常用回归有 9 组，大矩阵有 16448 组，包含全部 1 至 4096 位和 16 个更宽的边界值。
四种运算分别放在 `configs/ip/ilvector_logic/matrices/` 下，不与其他 IP 混放。

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type ilvector_logic
python3 scripts/run_all.py --config configs/ip/ilvector_logic/extended.json --list-cases
python3 scripts/run_all.py --all --case ilvector_logic_not65536
```

创建后检查实际 `.bd` 的参数、端口和接线，再运行公共 XSim 行为仿真。
JSON 中超过 13000 位的数值用十六进制字符串保存；仿真输入文件仍是完整二进制。

运算定义见 [UG994 向量逻辑](https://docs.amd.com/r/en-US/ug994-vivado-ip-subsystems/Utility-Vector-Logic)，
Inline 形式见 [UG994 Inline HDL](https://docs.amd.com/r/en-US/ug994-vivado-ip-subsystems/Inline-HDL)。
本机 2025.2 的实际参数另核对了 `data/rsb/iprepos/ilvector_logic_v1_0/component.xml` 和生成的 `.bd`。

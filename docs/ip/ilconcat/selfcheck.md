# Inline Concat 自检

对象是 `xilinx.com:inline_hdl:ilconcat:1.0`，不是旧版 `xlconcat`。
新版和旧版各自创建、仿真和报告，不合并测试结果。

## 参数和检查

`input_widths` 依次指定 In0、In1 等输入的宽度。支持 1 至 128 路，每路 1 至 4096 位。
所有端口都是向量，包括 1 位端口；没有时钟、复位或握手信号。
In0 放在 dout 最低位，之后的输入依次放到更高位。
Python 按这个位序独立计算期望值，不读取生成的 HDL 来决定答案。

输入包括全零、全一、各端口边界、随机数据和逐位标识序列。
逐位标识序列让不同输入位在一段时间内呈现不同的 0/1 序列，用来发现接错位和丢位。
小输入空间用穷举。其余参数用定向随机，预算随端口数增加。

常用回归有 6 组，大矩阵有 10872 组不同宽度数组：

- 全部 1 至 128 路端口数，配合 33 种字节、字长和上限边界宽度。
- 部分端口数下，逐个位置放置不同宽度的输入。
- 三路输入的混合宽度组合。

128 路、每路 4096 位也在可选矩阵中。这个配置的文本输入输出会占用数 GB 磁盘。
矩阵不是全部输入的穷举，也不表示其中每组配置都已经运行。

## 运行

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type ilconcat
python3 scripts/run_all.py --config configs/ip/ilconcat/extended.json --list-cases
python3 scripts/run_all.py --config configs/ip/ilconcat/extended.json --case ilconcat__input_widths_n128_w4096
```

创建时使用 Inline HDL 的 Block Design。框架检查 `.bd` 中的模块标识、参数、端口和直连关系，
再调用公共 XSim 行为仿真入口。不会生成假 XCI，也不会运行综合。
生成的 `.bd` 和行为 HDL 随本次运行归档。

运行时会核对当前 Vivado 的组件参数和生成的 `.bd`。
Inline HDL 的使用方式见 [UG994](https://docs.amd.com/r/en-US/ug994-vivado-ip-subsystems/Inline-HDL)。
旧版 128 路问题见[独立复现记录](../xlconcat/port_128_issue.md)，不能归到新版名下。

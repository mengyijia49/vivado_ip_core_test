# Inline Slice 自检

对象是 `xilinx.com:inline_hdl:ilslice:1.0`。输入为 Din，输出为 Dout；
两者都是向量，没有时钟、复位或握手信号。

## 参数和检查

- `input_width`：2 至 4096。
- `low_bit`、`high_bit`：满足 `0 <= low_bit <= high_bit < input_width`。
- 输出包含首尾两位，宽度为 `high_bit - low_bit + 1`。

Python 用右移和掩码算期望值。单元测试另用二进制字符串切片核对小位宽的所有输入。
仿真输入包含每个选中位的单独翻转、相反模式、相邻未选位干扰、逐位标识序列和随机值。

本机 XML 的静态上限是 255，但安装包的 Tcl 会随输入宽度改变范围。
2026-09-15 实际创建和功能仿真均接受第 4095 位，因此插件按输入宽度校验，
不会错误地把高 3840 位排除在测试之外。
创建探测编号为 `2026-09-15_05-38-08_UTC+0800_76d20837`。

常用回归有 7 组，大矩阵有 31119 组不同参数：

- 输入宽度 2 至 32 的全部合法截取区间。
- 输入宽度 33 至 4096 的最低位、最高位、完整输入、高端字节及中间位。
- 字节、字长及 256/512/1024/2048 位边界附近的跨界截取。

## 运行

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type ilslice
python3 scripts/run_all.py --all --case ilslice_high4096
python3 scripts/run_all.py --config configs/ip/ilslice/extended.json --list-cases
```

框架检查实际 `.bd` 的参数、输出宽度和直连关系，再做行为仿真。
范围依据为本机 `data/rsb/iprepos/ilslice_v1_0/` 下的 XML 和 `xgui/ilslice_v1_0.tcl`，
高位能力另有上述实测。Inline HDL 说明见
[UG994](https://docs.amd.com/r/en-US/ug994-vivado-ip-subsystems/Inline-HDL)。

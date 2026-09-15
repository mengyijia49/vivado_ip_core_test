# Inline 归约逻辑自检

对象是 `xilinx.com:inline_hdl:ilreduced_logic:1.0`，与旧版 `util_reduced_logic` 分开测试。
Op1 是 `width` 位向量输入，Res 是单比特标量输出。没有时钟、复位或握手。

`operation` 支持三种运算：

- `and`：所有输入位都是 1 时输出 1。
- `or`：至少一位是 1 时输出 1。
- `xor`：输入中 1 的个数为奇数时输出 1。

Python 独立计算结果；小位宽用所有输入检查模型。
仿真除了边界和随机值，还逐个输入位发出单独为 1、单独为 0 的模式。
这能检查某一位是否被遗漏。只用密集随机数据，很难发现归约与、归约或漏掉一位的问题。

## 参数范围

框架目前接受 1 至 65536 位，不把这个范围称为厂商上限。
本机参数校验要求宽度大于零，没有明确最大值；65536 位已完成创建和异或自检。
常用回归有 10 组，大矩阵有 12336 组，包含全部 1 至 4096 位和 16 个更宽边界值。

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type ilreduced_logic
python3 scripts/run_all.py --config configs/ip/ilreduced_logic/extended.json --list-cases
python3 scripts/run_all.py --config configs/ip/ilreduced_logic/extended.json --case ilreduced_logic_xor__width_65536
```

宽配置的成本不只取决于随机预算：逐位模式还会增加约 `2 * width` 次观察。
65536 位配置需要数 GB 输入文件及额外归档空间，不适合用来快速检查安装环境。
报告中的定向序列次数和实际输出行数分别保存，不把它们算成随机生成次数。

运算定义见 [UG994 归约逻辑](https://docs.amd.com/r/en-US/ug994-vivado-ip-subsystems/Utility-Reduced-Logic)。
本机参数依据为 `data/rsb/iprepos/ilreduced_logic_v1_0/` 下的 XML、Tcl 和创建探测所得 `.bd`。

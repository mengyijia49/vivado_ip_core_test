# Floating-Point 检查

`floating_point` 对应 Floating-Point Operator 7.1，目前接入九种功能：
Absolute、Float_to_float、Fixed_to_float、Float_to_fixed、Square_root、Compare、Add_Subtract、Multiply、Divide。
只做行为仿真。

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type floating_point
python3 scripts/run_all.py --config configs/ip/floating_point/matrices/float_to_fixed.json --limit 3
```

第一条运行 78 组常用配置。第二条只选浮点转定点矩阵的前 3 组。
各功能有独立矩阵入口，不需要修改公共配置，也不自动增加种子。

## 参数

前五种功能用 `input_exponent`、`input_fraction` 描述输入，`output_exponent`、`output_fraction` 描述输出。
浮点的 fraction 包含隐含首位，例如单精度是 8、24，总共 32 位。
定点的 exponent 表示含符号位的整数位数，fraction 表示小数位数，例如 8、9 共 17 位。
无符号定点输入只支持 Uint32、Uint64，通过 `input_unsigned` 选择。

| 矩阵 | 参数组数 | 范围 |
| --- | ---: | --- |
| absolute | 20640 | 全部 645 种合法浮点格式，最高 80 位 |
| float_to_float | 171264 | 各格式与单精度互转，另有典型格式交叉转换 |
| fixed_to_float | 206624 | 4 至 64 位定点的全部小数位位置，32/64 位有符号和无符号整数 |
| float_to_fixed | 678656 | 单/双精度转各定点格式，各浮点格式转 32/64 位整数 |
| square_root | 1390016 | 全部 645 种浮点格式，各自全部合法运算间隔 |
| compare | 1191960 | 全部 645 种浮点格式，八种固定模式及可编程模式，各路侧带和包尾组合 |
| add_subtract | 407472 | 全部格式，固定加/减及可编程加减，支持的架构与 DSP 组合、13 种侧带配置 |
| multiply | 402896 | 全部格式，支持的架构与 DSP 组合、13 种侧带配置 |
| divide | 3578240 | 全部格式与合法运算间隔，四种异常位开关、五种侧带配置 |

合计 8047768 组不同参数，不是所有输入输出格式的完整交叉乘积。
其中也包含运算间隔、侧带、异常标志和 AXI 优化设置的变化。
不同运算仍属于同一类 IP，不把它们计作九类 IP。
这些是待选参数，不代表全部完成仿真。

## 怎么比较

Python 用整数拆分符号、指数和尾数，精确计算二进制移位及最近偶数舍入。
不使用厂商模型生成期望值。单元测试另用宿主 IEEE 转换和有理数计算交叉检查。
定向输入覆盖正负零、次正规数、最小正规数、最大有限数、无穷、两类 NaN、
舍入中点两侧、舍入进位、饱和边界及输入补齐位。

按 [PG060](https://docs.amd.com/v/u/en-US/pg060-floating-point)，普通转换把次正规输入当作带符号的零；
绝对值则保留次正规数和 NaN 载荷。数值运算的输出补齐位做符号扩展；比较结果补零。
浮点转定点使用最近偶数舍入，越界时饱和；NaN、无穷和普通越界的异常标志分别检查。
下溢采用[舍入后判断](underflow_review.md)，该处的手册冲突单独保留。
数据、补齐位、异常标志和用户侧带全部比较，没有放宽误差或使用输出掩码。

Blocking 接口检查有效握手、收发数量、顺序和回压期间的稳定性。
三种转换和平方根在启动时复位；Absolute 没有时钟和复位端口，testbench 按固定节拍采样。
实际输入接收记录和输出文件由 Python 再次核对。

## 平方根

```bash
python3 scripts/run_all.py --config configs/ip/floating_point/regression/square_root.json
python3 scripts/run_all.py --ip-type floating_point --case fp_sqrt80_rate65
```

平方根的 `cycles_per_operation` 默认 1，允许 1 至 `input_fraction + 1`；
除法允许 1 至 `input_fraction + 2`，其他已接入运算仍只允许 1。
输入输出格式必须相同。平方根只有 INVALID_OP 可选异常位，插件会拒绝无效标志。
矩阵按指数、精度分目录，单个文件不超过 4160 组，不把低速配置复制成新的 IP 类型。

参考先求整数平方根，再比较精确的舍入中点平方，支持 80 位格式。
定向输入包含完全平方及其相邻输入、舍入阈值两侧、奇偶指数和正负特殊值。
负零、负次正规数、负正规数、负无穷和 NaN 分别检查。
低速配置仍由 READY 决定输入接收，不按猜测的延迟丢掉输入。
超时随运算间隔增加；最后一次输出后继续观察，检查多发。
这不是固定延迟或吞吐率性能测试，也不检查运行中复位。

## 比较

比较使用独立的参数格式和多输入驱动，详见[比较器检查](compare.md)。
A、B 和可选 OPERATION 各自握手、各自推进，不要求一组全部完成才能发送下一组。
既检查七种布尔比较，也检查条件码；可编程配置会对每组数值执行七种合法操作。

## 加减和乘法

使用独立整数参考和公共多输入驱动，配置与限制见[加减和乘法检查](arithmetic.md)。
低延迟双精度乘法有[待确认数值差异](multiply_rounding_issue.md)，原样报告失败。

## 除法

除法用整数商和余数决定舍入，单独处理除零及无效运算，详见[除法检查](divide.md)。
低速实现仍按各路 READY 驱动输入，不根据估计的延迟跳过检查。

尚未接入融合乘加等其他运算，也没有接入 NonBlocking、ACLKEN、
运行中复位和手动延迟。当前使用自动延迟，不断言固定输入到输出周期数。
所有请求参数和实际端口均与 XCI 核对，实际模型延迟保存在运行归档。

真实运行和检查记录见[转换接入检查](../../experiments/floating_point_acceptance.md)
及[平方根接入检查](../../experiments/floating_point_sqrt_acceptance.md)、
[比较接入检查](../../experiments/floating_point_compare_acceptance.md)、
[加减和乘法接入检查](../../experiments/floating_point_arithmetic_acceptance.md)。

# Floating-Point 检查

`floating_point` 对应 Floating-Point Operator 7.1，目前接入十四种功能：
Absolute、Float_to_float、Fixed_to_float、Float_to_fixed、Square_root、Compare、Add_Subtract、Multiply、Divide、FMA、Reciprocal、Reciprocal_square_root、Exponential、Logarithm。
只做行为仿真。

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type floating_point
python3 scripts/run_all.py --config configs/ip/floating_point/matrices/float_to_fixed.json --limit 3
```

第一条运行 98 组常用配置。第二条只选浮点转定点矩阵的前 3 组。
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
| fma | 96 | 半、单、双精度，融合加/减、两种 DSP 用量和三种异常位开关 |
| reciprocal | 96 | 半、单、双精度，两种 AXI 优化、侧带和两个异常位开关 |
| reciprocal_sqrt | 96 | 半、单、双精度，两种 AXI 优化、侧带和两个异常位开关 |
| exponential | 96 | 半、单、双精度，两种 AXI 优化、侧带、下溢和上溢开关 |
| logarithm | 96 | 半、单、双精度，两种 AXI 优化、侧带、无效运算和除零开关 |

合计 8048248 组不同参数，不是所有输入输出格式的完整交叉乘积。
其中也包含运算间隔、侧带、异常标志和 AXI 优化设置的变化。
不同运算仍属于同一类 IP，不拆成多个 IP 类型计数。
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
数据、补齐位、异常标志和用户侧带全部比较。倒数和倒数平方根按 PG060 的精度范围评分：
半精度仍逐位相等，单、双精度的普通数值允许 1 ULP；特殊值和侧带仍逐位相等。
指数和自然对数的普通有限结果允许 1 ULP，三种精度采用同一规则；特殊值、异常标志和侧带逐位相等。

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

## 融合乘加和融合乘减

FMA 使用 A、B、C 和 OPERATION 四个独立 AXI-Stream 输入。操作码 0 计算 `A*B+C`，
操作码 1 计算 `A*B-C`。testbench 分别推进四路握手，不假定它们在同一周期到达。
Python 参考先精确计算乘积与加减，只对最终结果做一次最近偶数舍入，
因此可以检查先乘后舍入再相加无法覆盖的情况。

当前只覆盖原生半精度、单精度和双精度，使用速度优化及 Medium/Full DSP 用量。
定向输入包含零、次正规数、无穷、NaN、上溢、下溢、抵消和融合舍入差异，
并检查异常标志、各输入的 TUSER/TLAST、输出侧带顺序和回压保持。

## 倒数

Reciprocal 计算 `1/A`。参考模型使用精确整数除法，只在结果编码时做一次最近偶数舍入。
当前只支持输入输出格式相同的原生半、单、双精度。格式不同的 XCI 虽能生成，
当前不把异格式组合作为已覆盖项。

精度判定以 PG060 给出的范围为准；2026.1 的实际结果见
[全量报告](../../experiments/vivado_2026_full_regression.md)。

## 倒数平方根

Reciprocal square root 计算 `1/sqrt(A)`。参考模型使用整数平方根和精确中点平方比较，
不调用宿主浮点运算。当前只支持输入输出格式相同的原生半、单、双精度。
异格式 XCI 虽能生成，但当前不把它们作为已覆盖项。

定向输入覆盖正负零、次正规数、正负无穷、NaN、负数、指数边界和舍入边界。
INVALID_OP、DIVIDE_BY_ZERO、TLAST 和 TUSER 单独检查。四组代表配置的创建、
testbench 生成和行为仿真均通过，见
[全量报告](../../experiments/vivado_2026_full_regression.md)。

## 指数和自然对数

Exponential 计算 `e^A`，Logarithm 计算自然对数 `ln(A)`。Python 用 180 位和 260 位
十进制精度各算一次，只有两次编码结果一致才生成期望值。定向输入包含零、次正规数、
无穷、NaN、负数、1、2、0.5、`ln(2)` 附近以及指数上溢和下溢边界。

当前只保留输入输出格式相同的原生半、单、双精度。指数检查 UNDERFLOW 和 OVERFLOW，
对数检查 INVALID_OP 和 DIVIDE_BY_ZERO。两者没有复位端口。6 组代表配置的 18 个阶段通过，
见[全量报告](../../experiments/vivado_2026_full_regression.md)。

尚未接入其他运算，也没有接入 NonBlocking、ACLKEN、
运行中复位和手动延迟。当前使用自动延迟，不断言固定输入到输出周期数。
所有请求参数和实际端口均与 XCI 核对，实际模型延迟保存在运行归档。

所有常用配置的实际结果见
[Vivado 2026.1 全量报告](../../experiments/vivado_2026_full_regression.md)。

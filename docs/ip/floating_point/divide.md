# 浮点除法检查

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --config configs/ip/floating_point/regression/divide.json
python3 scripts/run_all.py --ip-type floating_point --case fp_div80_rate66
python3 scripts/run_all.py --config configs/ip/floating_point/matrices/divide.json --limit 3
```

第一条运行 12 组常用配置，第二条只测 80 位低速除法，第三条选大矩阵前 3 组。
大矩阵仍需完整校验。先测一小部分时，可将第三条路径换成
`configs/ip/floating_point/matrices/divide/e16/p64.json`。
这是 Floating-Point Operator 的 `Divide`，不是整数 Divider Generator。
两者的模型和配置分开，不把一种运算的结果当作另一种的结果。

## 参数

输入、输出使用同一浮点格式。`input_exponent` 为指数位数，
`input_fraction` 包含隐含首位；范围与其他浮点运算一样，最高 80 位。
`cycles_per_operation` 必填，允许 1 至 `input_fraction + 2`。
使用 Blocking、启动复位、自动最大延迟，不接入手动延迟、ACLKEN 或运行中复位。

本机 2025.2 将 Low_Latency 和 DSP 使用请求改回固定实现，因此配置不提供这些伪选项。
请求和实际 XCI 仍会核对。`optimization` 只选择 AXI 接口的 Resources 或 Performance。

可选矩阵共 3578240 组：645 种格式、各自全部合法运算间隔、两种 AXI 优化目标、
UNDERFLOW/OVERFLOW/INVALID_OP/DIVIDE_BY_ZERO 的全部开关组合，以及五种侧带配置：
无侧带、A 包尾、B 包尾、两路 OR 包尾、256 位 USER 加两路 AND 包尾。
后四种都带 A/B USER，检查结果异常位与用户位之间的拼接位置。
定向 USER 使用全宽变化模式，原有窄通道覆盖缺口见[修正说明](user_patterns.md)。
矩阵按指数、精度分目录，每个叶文件不超过 10560 组。
这不是全部 USER 宽度的交叉乘积，也不是已经运行完的配置数量。

## 数值参考

Python 拆出符号、指数和尾数，用整数除法求商、余数。
将两倍余数与除数比较，决定最近偶数舍入，不通过宿主浮点数计算期望。
超宽指数也不依赖宿主浮点数的范围。

按 [PG060](https://docs.amd.com/v/u/en-US/pg060-floating-point) 的异常规则，
有限非零数除以零才置 DIVIDE_BY_ZERO；0/0 和无穷/无穷置 INVALID_OP。
无穷除以零不置 DIVIDE_BY_ZERO；NaN 先按静默 NaN 处理。
次正规输入按带符号零处理，故非零数除以次正规数也会触发除零。
上溢、下溢、结果符号和补齐位均检查；[下溢手册歧义](underflow_review.md)继续单独记录。

定向前缀包括特殊值交叉、相邻尾数、指数范围边界、相等输入和循环小数。
另用模逆构造“余数最接近除数一半”的输入，分别接近舍入中点两侧，避免只测容易整除的值。
常用 8 位配置在运算间隔 1、6 下分别穷举全部 65536 组数值对。
其他常用配置使用 1024 个策略输入，加上定向前缀；实际拍数以报告为准。

## 握手

A 和 B 独立到达、独立握手，按各自的第 n 次接收配对。
存在输入停顿和输出长回压，检查未知值、回压保持、多发、漏发及过早输出。
没有 OPERATION 输入，不允许配置其 USER 或 TLAST。
只在结果有效握手时比较数值及侧带，最后由 Python 再核对实际接收输入。
超时预算随运算间隔增加，不用延迟估计代替 READY，也不把低速输出当作漏发。

参数探测记录位于 `reports/framework/floating_divide_probe/2026-09-15_13-39-25_UTC+0800_1802dca9/summary.json`。
其中 7、67 周期的越界请求被正确拒绝，不计为 bug；失败工程回退后的默认 XCI 也不算请求成功。

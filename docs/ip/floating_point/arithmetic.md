# 浮点加减和乘法检查

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --config configs/ip/floating_point/regression/add_subtract.json
python3 scripts/run_all.py --config configs/ip/floating_point/regression/multiply.json
python3 scripts/run_all.py --config configs/ip/floating_point/matrices/multiply.json --limit 3
```

前两条分别运行 9 组加减、7 组乘法。第三条只选乘法大矩阵前 3 组。
加减、乘法的配置分开存放，仍属于 `floating_point`，不另算 IP 类型。

## 参数范围

`input_exponent` 是指数位数，`input_fraction` 包含隐含首位。A、B 和结果格式相同。
支持全部 645 种合法格式，从 8 位到 80 位；半、单、双精度用 Vivado 原生精度选项。
`Add_Subtract` 还需 `add_sub_value=Add/Subtract/Both`；乘法不接受这个参数。

| 运算与格式 | Speed_Optimized 的 DSP 选项 | Low_Latency 的 DSP 选项 |
| --- | --- | --- |
| 加减，半/单精度 | No、Medium、Full | No |
| 加减，双精度 | No、Full | No |
| 加减，其他格式 | No | 不接入 |
| 乘法，双精度 | No、Medium、Full、Max | Max |
| 乘法，其他格式 | No、Full、Max | 不接入 |

表中 DSP 选项在配置里写作 `No_Usage` 等。部分无效请求会被 Vivado 悄悄改写，
插件提前拒绝这些组合，并用实际 XCI 再核对。范围以本机 Vivado 2025.2、Artix-7 为准。
`optimization=Resources/Performance` 是 AXI 接口优化目标，不是上表的运算架构。
只接入 Blocking、启动复位、自动最大延迟、每周期可发起一次运算。
尚不接入手动延迟、ACLKEN、运行中复位或其他运算间隔。

矩阵覆盖所有合法格式和上表实现方式，再组合三种异常位的全部开关、两种 AXI 优化目标，
以及 13 种代表侧带配置。加减共 407472 组，乘法共 402896 组。
侧带包含单路、各路组合、256 位 USER 和不同 TLAST 来源，并非所有宽度的完整交叉乘积。
文件继续按运算、实现方式和指数拆分，每个叶文件不超过 13312 组。

## 输入与比较

Python 先精确对齐整数尾数做加减，或求整数乘积，最后只舍入一次。
最近偶数、正负零、抵消、NaN、无穷、溢出和无效操作均单独处理。
次正规输入当作带符号的零；下溢规则的手册冲突仍[单独记录](underflow_review.md)。
依据是 [PG060](https://docs.amd.com/v/u/en-US/pg060-floating-point) 的 IEEE 偏差、
精度和异常标志章节，不用厂商模型生成期望值。

定向前缀覆盖特殊值交叉、指数差、舍入中点两侧、进位、抵消和范围边界，随后加入策略输入。
`Both` 对每组数值执行加、减两种合法操作；操作码高两位补齐区也会变化。
A、B 的输入补齐位分别改变，输出补齐位必须正确符号扩展。
默认 1024 是策略预算，不含定向前缀和每组追加操作；实际检查拍数以报告为准。
四个 8 位常用配置穷举 65536 组数值对；`Both` 每对检查两次。

A、B、可选 OPERATION 各有独立游标和握手，不等待整组全部接收才发下一组。
测试中会拉开各路到达时间，并长时间回压输出。检查顺序配对、未知值、稳定性、多发和漏发。
TUSER 按已启用的异常位、A、B、OPERATION 顺序拼接；TLAST 按配置单独计算。
定向 USER 的全宽变化和旧版覆盖缺口见[修正说明](user_patterns.md)。
没有放宽数值误差，也没有把未输出的数据算成已比较。

双精度低延迟乘法已有[独立复现](multiply_rounding_issue.md)，不会为了让回归全绿而移除配置。

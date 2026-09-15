# 浮点加减和乘法接入记录

2026-09-15，Ubuntu 22.04、Vivado 2025.2、Artix-7 行为仿真。
新增加减和乘法的独立整数参考、16 组常用配置、810368 组可选参数。
这是同一类 Floating-Point IP 的功能扩展，不新增 IP 类型，也不代表大矩阵全部实跑。

## Python 和配置检查

`python3 -m py_compile scripts/run_all.py` 通过。
`PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v`：
640 项中 464 项通过，176 项真实 Vivado 集成测试按默认设置跳过。
这里的通过数量不包含下面单独启用的真实仿真。

包含 5894650 组参数的完整合法性和去重检查，耗时 916.553 秒，子进程峰值内存约 7.57 GiB。
检查前后 287 份运行源码、220 份测试文件和 1415 份配置文件哈希一致。
加减、乘法的小格式全部数值对另与独立舍入网格交叉检查，原生精度用宿主 IEEE 运算对照。
记录：`reports/framework/floating_arithmetic_validation/2026-09-15_13-21-30_UTC+0800_b22b7727/summary.json`。

## 真实 IP

分两批运行全部 16 组新增常用配置，共 48 个阶段，47 PASS、1 SIMULATION_FAILED。

| 批次 | 配置 | 结果 |
| --- | --- | --- |
| `2026-09-15_12-54-17_UTC+0800_f23eb1d7` | 8 位加法、9 位可编程加减、8 位乘法、低延迟双精度乘法 | 前三组通过，低延迟乘法数值失败 |
| `2026-09-15_13-17-32_UTC+0800_72b33731` | 其余 12 组，包含小格式穷举、半/单/双精度和 80 位 | 36 个阶段通过 |

15 组通过配置共比较 450411 个输出，实际接收输入与输入文件完全一致。
8 位加、减、可编程加减、乘法分别包含全部 65536 组数值对；可编程加减每对检查两次。
定向前缀仍保留，因此实际输出数大于策略预算。
低延迟乘法在第 2246 个输出发现差异，后续缺失不能算作更多独立 bug。

两批归档分别核对 287 份源码和 449、768 份产物哈希。
首批之后仅增加双精度加减禁止 Medium DSP 的参数限制，未改数值参考或握手。
核对记录：`reports/framework/floating_arithmetic_audit/2026-09-15_13-24-42_UTC+0800_c5862274/summary.json`。

## 数值异常

双精度 `Low_Latency + Max_Usage` 的某些乘积应舍入为 1.0，实测约 0.5。
固定输入独立 VHDL 两次复现，速度优化两种 DSP 对照通过。
厂商 C 数值模型也与写死的期望一致，未用它替代框架参考。
详细输入、参数和命令见[乘法差异记录](../ip/floating_point/multiply_rounding_issue.md)。
目前按一条待确认问题保留，不把五个符号或缩放变体计为五个 bug。

另外核对五组单、双精度加减或乘法的 38502 个期望输出，厂商 C 数值模型的结果和
已启用异常位全部一致，包括低延迟配置尚未实际输出的期望值。
这只是参考交叉检查，不能把这些尚未输出的数据算作 DUT 通过。
记录：`reports/framework/floating_arithmetic_cmodel/2026-09-15_13-29-28_UTC+0800_de3b13fc/summary.json`。

## 兼容性

比较器的多输入驱动提取到 `multi_input/`，原有入口继续兼容。
对比改造前快照，17 组比较配置的设置和模型参数一致；119 个输入、期望、
时序及 VHDL 文件在归一化绝对路径后完全一致。manifest 未参与逐字比较。
记录：`reports/framework/floating_compare_compatibility/2026-09-15_13-22-58_UTC+0800_a7e377e0/summary.json`。

已从独立源码副本构建 wheel 并解包检查，公共多输入模板、比较兼容入口和整数参考均可加载。
没有改写工作区源码；记录为 `reports/framework/package_check/2026-09-15_13-20-57_UTC+0800_739ab860/summary.json`。

## 故障检出检查

独立加减 VHDL 的 12 个写死期望例子通过，覆盖零符号、舍入中点、进位、下溢、
上溢、无效操作、NaN、独立输入、异常位、USER 和 TLAST。它不调用 Python 数值参考。
原有比较器的独立真实 IP 对照也通过。

加减、比较各运行一个正常伪模块和 13 种人为故障：数值、USER、TLAST、未知值、
回压期间变化、漏发、多发、过早输出、VALID 撤销、READY 未知、操作码错误、
异常位错误或比较结果补齐错误、丢失操作数。
两组正常模块通过，26 种故障全部按预期失败，不能将这些故障计作 IP bug。

四个集成测试方法通过，共约 502 秒；检查前后 287 份运行源码哈希一致。
日志和汇总：`reports/framework/floating_arithmetic_injection/2026-09-15_13-24-04_UTC+0800_becc9496/summary.json`。

## 默认回归

运行 `python3 scripts/run_all.py`，批次 `2026-09-15_13-32-47_UTC+0800_53889cbd`。
原有六组 Divider/Multiplier 的 19 个阶段全部通过，18 个输入、期望和实际输出文件
与改造前一致；287 份源码、525 份归档文件哈希核对通过。
检查记录：`reports/framework/floating_arithmetic_default_audit/2026-09-15_13-35-40_UTC+0800_70bc40ff/summary.json`。

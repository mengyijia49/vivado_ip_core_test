# 浮点除法接入检查

2026-09-15，Ubuntu 22.04、Vivado 2025.2、Artix-7 行为仿真。
新增 Floating-Point Operator 的 Divide，不是新增一类整数 Divider IP。
参考、参数和定向输入分别放在 `floating_point/divide/`。

## 范围

新增 12 组常用配置、3578240 组可选参数；大矩阵没有全部实跑。
覆盖 645 种格式、全部合法运算间隔、四种异常位的开关组合、两种 AXI 优化和五种侧带配置。
整体为 36 类 IP、323 组常用配置、9472890 组可选参数，默认仍是六组 Divider/Multiplier。
具体命令和限制见[除法说明](../ip/floating_point/divide.md)。

## 真实除法

首批 `2026-09-15_13-49-13_UTC+0800_e7d78c62`：12 组、36 个阶段全部通过，
比较 204949 个输出，实际接收输入与输入文件一致。
两组 8 位配置分别以 1、6 周期运算间隔穷举全部 65536 组数值对，另保留定向前缀。
其他配置覆盖 9 位补齐、半/单/双精度和 80 位格式，以及最高 66 周期运算间隔。

首批之后发现并修正定向 USER 的窄通道覆盖缺口，见[USER 修正](../ip/floating_point/user_patterns.md)。
首批使用的是旧标签，不能替代修正后的回归。数值参考和握手机制没有因实测结果而放宽。

修正后批次 `2026-09-15_14-12-36_UTC+0800_8a3888a1` 重跑全部 25 组受影响配置：
8 组比较、5 组加减、4 组乘法和 8 组除法。75 个阶段中 74 PASS，
只有原有 `fp_mul64_low` 数值失败，仍在同一输入的第 2246 个输出，USER 和 TLAST 一致。
这是已有[乘法线索](../ip/floating_point/multiply_rounding_issue.md)，不新增问题计数。
其余 24 组共比较 430383 个输出，其中除法 59215 个；实际接收输入均与文件一致。
292 份源码和 1294 份产物哈希通过核对：
`reports/framework/floating_user_audit/2026-09-15_14-28-15_UTC+0800_c83ae6b0/summary.json`。

另从已有矩阵选出 `(指数, 精度)` 为 `(16,4)`、`(5,13)`、`(6,29)`、`(7,61)`、`(8,64)`
的五组边界，全部使用最大运算间隔、256 位 A/B USER 和四种异常位。
批次 `2026-09-15_14-26-36_UTC+0800_c1a84b21` 的 15 个阶段全通过，比较 84413 个输出。
它们是已有矩阵的抽样，不再次增加参数计数，也没有改动常用 12 组配置。
292 份源码和 493 份产物哈希一致；核对记录：
`reports/framework/floating_divide_boundary_audit/2026-09-15_14-32-34_UTC+0800_e9c84b66/summary.json`。

## 独立检查

33 项针对性单元测试通过。8 位除法全部数值对与独立 Fraction 舍入网格核对；
原生格式另与宿主 IEEE 运算交叉检查，超宽格式不用宿主浮点数计算期望。
所有精度的定向商余数构造均检查舍入中点两侧。

手写 VHDL 不调用 Python 数值参考，用 16 个固定期望检查循环小数、正负零、
NaN、无穷、上溢、下溢、除零和无效操作；运算间隔 1、26 的真实 IP 均通过。
另用一个正常伪模块和 13 种人为故障检查数值、USER、TLAST、异常位、未知值、
回压保持、漏发、多发、过早输出、VALID 撤销、READY 未知和丢失操作数。
正常模块通过，全部故障按预期被检出。这些人为故障不计作 IP bug。

三个集成测试方法通过，耗时 275.693 秒。
记录：`reports/framework/floating_divide_integration/2026-09-15_14-07-23_UTC+0800_c3865c85/summary.json`。
首批 292 份源码、773 份归档文件及 16 个独立对照/故障注入归档均核对哈希。
核对记录：`reports/framework/floating_divide_audit/2026-09-15_14-16-37_UTC+0800_b25b830d/summary.json`。

## 参考交叉核对

五组单、双精度除法共 31149 个数值和已启用异常位与厂商 C 数值模型一致。
它只作额外对照，不生成框架期望，也不能替代真实 IP 的协议检查。
记录：`reports/framework/floating_divide_cmodel/2026-09-15_14-15-51_UTC+0800_e95c441e/summary.json`。
首次临时核对命令误把 TLAST 当作 USER；已改为读取 manifest 的字段布局后重查，未改历史产物。

## 兼容与打包

对比改造前快照，33 组比较、加减、乘法的设置、模型参数、数值输入、操作码、
TLAST、数值期望、异常位、输入间隔、回压和 VHDL 保持一致。
USER 有意改变，已按输入独立重算拼接关系，不要求整份输入和期望文件逐字相同。
记录：`reports/framework/floating_user_compatibility/2026-09-15_14-09-46_UTC+0800_40e51067/summary.json`。

独立源码副本构建的 wheel 可加载除法模块及公共多输入模板。
记录：`reports/framework/package_check/2026-09-15_14-15-52_UTC+0800_f7292d7f/summary.json`。
首次临时命令写错了模板文件名，修正检查后通过，没有修改包代码。

## 完整检查

`python3 -m py_compile scripts/run_all.py` 通过。
完整 unittest 共 656 项：477 项通过，179 项真实 Vivado 集成测试按默认设置跳过。
其中包含 9472890 组参数的完整合法性及去重检查，耗时 1273.248 秒，
子进程峰值内存约 12.24 GiB，不能把它称作轻量检查。
检查前后 292 份运行源码、226 份测试文件、2076 份配置文件哈希一致。
记录：`reports/framework/floating_divide_validation/2026-09-15_14-08-22_UTC+0800_321411ff/summary.json`。

默认运行 `python3 scripts/run_all.py`，批次 `2026-09-15_14-32-33_UTC+0800_d0a67afd`
的六组 Divider/Multiplier、19 个阶段全通过，耗时约 144 秒。
18 个输入、期望和实际输出文件与改造前一致，292 份源码、530 份产物哈希核对通过。
记录：`reports/framework/floating_divide_default_audit/2026-09-15_14-35-20_UTC+0800_76eeb4cb/summary.json`。

本轮没有新增已确认的 IP bug。新增除法未观察到异常；已有低延迟浮点乘法仍可复现。
USER 覆盖缺口、临时核对命令错误和人为故障均不计入厂商问题。

# CORDIC 平方根接入检查

2026-09-15，Vivado 2025.2，CORDIC 6.0，器件 xc7a35tcsg324-1。只做行为仿真。
新增 Blocking 平方根接口、整数数学参考、平方数及舍入边界输入。
接口规则和限制见[平方根检查](../ip/cordic/selfcheck.md)。

## 配置范围

新增 11 组常用配置、661248 组不同参数，其中整数 15744 组、定点 645504 组。
全部完成配置、参数约束和测试预算检查，没有全量运行 Vivado。
工程累计 33 类 IP、224 组常用配置、1416102 组扩展参数。
这些数字不表示已经完成的仿真次数，也不表示发现了多少 bug。

## 真实 IP 回归

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type cordic
python3 scripts/run_all.py --config configs/ip/cordic/diagnostics/rounding_controls.json
```

常用回归编号 `2026-09-15_07-25-22_UTC+0800_a16a315d`：33 个阶段中 28 个 PASS，
5 个仿真阶段失败。6 组配置完整通过，5 组 Nearest_Even 配置出现数学舍入差异。
失败在首次不一致时停止，所以 16 位 Nearest_Even 配置没有完成全输入检查。
249 份源码和 695 个归档产物的哈希核对一致。

数学参考不是厂商位精确模型。手写 VHDL 和官方 C 模型复现了小输入的差异，
但内部精度规则尚待核实，不能把这 5 组失败计为 5 个 IP bug。
详细输入、复现命令和判断见[舍入差异审查](../ip/cordic/rounding_review.md)。
接入时还修正了框架对无符号输出补齐位的解释，按 PG105 改为符号扩展；
修正前的运行记录保留，该问题不计作厂商 bug。

三个独立舍入对照编号 `2026-09-15_07-29-34_UTC+0800_ebe87b2a`：9 个阶段全部 PASS。
16 位截断和就近向上舍入各检查 65622 次传输，均包含全部 65536 个不同输入值；
48 位截断检查 4325 次传输。输入接收记录与输出均通过核对。
249 份源码和 370 个归档产物的哈希核对一致。

## 检查器与兼容性

```bash
VIVADO_INTEGRATION=1 PYTHONPATH=src:tests python3 -m unittest \
  integration.ip.cordic.test_failure_detection -fv
```

两项测试通过，共十次 XSim，耗时约 160 秒。正确替身通过，八种人为错误被检出：
错误数值、未知位、回压期间数据变化、漏发、多发、错误 TLAST、TUSER 和补齐位。
另一次为真实 IP 的手写 VHDL 对照。人为错误只用于检查框架，不算 IP bug。

公共流接口增加端口前缀支持，原有默认端口名称不变。
兼容回归编号 `2026-09-15_07-31-24_UTC+0800_b0bfa1cd`：
`axis_reg_default8`、`axis_clock8`、`subset_reverse3_5` 的 9 个阶段全部 PASS。
输入、期望输出、间隔、READY 和向量记录与各自旧批次逐字节相同；
归一化运行路径后的 testbench 也相同。249 份源码、379 个归档产物的哈希一致。

## 框架检查

`python3 -m py_compile scripts/run_all.py` 通过。
完整 unittest 共 503 项，350 项通过、153 项真实工具测试按规则跳过，耗时约 680 秒。
默认 `python3 scripts/run_all.py` 编号 `2026-09-15_07-32-49_UTC+0800_0d38eb05`，
原有六组配置、19 个阶段全部 PASS。249 份源码、487 个归档产物的哈希一致。
`scripts/run_all.py` 和原有 Divider demo Tcl 没有修改。

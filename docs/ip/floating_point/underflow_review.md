# 浮点转换下溢规则

2026-09-15，Vivado 2025.2，Floating-Point Operator 7.1。
这是参考模型的规范解释记录，不是已经确认的 IP 实现 bug。

## 冲突在哪里

[PG060 第 12 页](https://docs.amd.com/api/khub/documents/ym1A7qsltTGP_saZFTrikQ/content)
的 UNDERFLOW 正文要求舍入后判断下溢，紧随其后的注释却要求舍入前的次正规结果归零。
当舍入进位恰好达到最小正规数时，两种解释不同。

单精度输入 `0x387ff000` 表示 `2^-14 - 2^-26`，转换到半精度时：

- 按注释，先判为过小，输出零并置 UNDERFLOW。
- 按正文，先按目标有效位数舍入，进位后输出 `0x0400`，不置 UNDERFLOW。

首批 `2026-09-15_07-52-17_UTC+0800_caff2173` 使用第一种解释，三个缩窄配置失败。
实际 IP 输出符合第二种解释。该批输入、参考、输出和源码归档没有改写。

## 当前处理

参考模型 `floating_point_conversion:1.1` 明确采用正文规则：先按目标有效位数舍入，
再检查结果指数；仍过小才输出带符号的零并置 UNDERFLOW。
这不是先按 IEEE 次正规格式舍入，不能直接把宿主的半精度转换当作整套参考。
例如 `0x387fe000` 在当前规则下仍归零。

报告的 `reference_contract` 记录 `underflow_detection` 和
`underflow_documentation_conflict`。此修改不是对个别观测值作特殊处理，
也没有忽略下溢位或扩大允许误差。其他数值规则保持不变。
需要厂商进一步说明注释适用范围，才能判断这是文档问题还是版本语义差异。

## 独立对照

`tests/fixtures/ip/floating_point/underflow_probe.vhd` 手写了 14 组输入和期望值，
包括进位阈值前后、正负号、次正规输入和最小正规数，不调用 Python 参考或生成器。

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
VIVADO_INTEGRATION=1 PYTHONPATH=src:tests python3 -m unittest \
  integration.ip.floating_point.test_failure_detection.FloatingFailureDetectionTests.test_handwritten_underflow_boundary_without_python_reference -v
```

该对照已通过，验证的是上面的明确规则，不代表解决了手册本身的冲突。
运行编号 `2026-09-15_08-01-26_UTC+0800_eec11539`，产物在
`runs/framework/protocol_probe/<编号>/floating_point/underflow_boundary/`，
日志位于对应的 `runs/logs/framework/protocol_probe/`。

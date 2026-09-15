# CORDIC 舍入差异审查

2026-09-15，Vivado 2025.2，CORDIC 6.0，Square_Root，自动迭代和自动内部精度。
这是一份数值差异记录，不是已确认的厂商 bug。

## 观察

8 位无符号整数输入、5 位结果字段，Nearest_Even 模式：输入 7 得到 2。
精确平方根约为 2.64575，直接按最近偶数规则舍入应为 3。
其他定点配置也出现比精确数学舍入值小一个最低位的结果。

补齐位规则修正后的批次 `2026-09-15_07-25-22_UTC+0800_a16a315d` 保留完整输入、输出和失败日志。
配置入口为 `configs/ip/cordic/regression.json`，失败不会被自动跳过或改成 PASS。
报告中的 `reference_contract` 明确标记 `vendor_bit_accurate: false`，
表示这是数学参考，不是对厂商内部运算过程的复刻。

## 为什么还不能算 bug

[PG105 第 40、41 页](https://docs.amd.com/api/khub/documents/NHMqdvRJIfgF8hdbQmLFuA/content)
分别规定输出舍入和内部精度；平方根的 Nearest_Even 默认内部精度比结果宽度多两位。
精确数学值舍入，与先保留有限位数再舍入，不一定相同。
例如先保留两位小数位，2.64575 变为 2.5，再取最近偶数会得到 2。
这是待验证的解释，不是已经证明的内部实现，也没有据此改写参考模型。

厂商 C 模型对输入 7 同样给出 2；另外两个就近舍入模式给出 3。
诊断编号 `2026-09-15_07-22-27_UTC+0800_f9b5f1bb`，输出位于
`runs/logs/framework/cmodel/<编号>/cordic/rounding/execute.log`。
调用程序为 `tests/fixtures/ip/cordic/cmodel_probe.c`，库由本机 Vivado 提供，未加入仓库。
编译命令、退出码、源码和库压缩包哈希另存于同目录的调用记录。
两种厂商模型一致只能说明差异不是当前 testbench 独有的问题，不能证明规范一定正确。

## 对照与后续

手写 `tests/fixtures/ip/cordic/nearest_even_probe.vhd` 不使用自动生成器或 Python 参考。
实测编号 `2026-09-15_07-26-46_UTC+0800_4bf52b55`，输入 7 同样得到 2。
通过以下测试创建真实 IP 并运行它，打印固定输入的完整输出字段：

```bash
VIVADO_INTEGRATION=1 PYTHONPATH=src:tests python3 -m unittest \
  integration.ip.cordic.test_failure_detection.CordicFailureDetectionTests.test_handwritten_probe_reproduces_nearest_even_difference -v
python3 scripts/run_all.py --config configs/ip/cordic/diagnostics/rounding_controls.json
```

第二条包含 16 位全输入空间的截断/就近向上舍入对照和 48 位截断对照。
实测编号 `2026-09-15_07-29-34_UTC+0800_ebe87b2a`，三个对照均通过。
不要把多种参数下的同类差异计成多个独立 bug。
下一步需确定手册对误差和最终舍入的完整保证，再决定是规范允许的量化、
文档歧义还是实现问题；在此之前保留数学差异和待审查状态。

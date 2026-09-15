# FIFO FWFT 接入检查

2026-09-15，Vivado 2025.2，器件 xc7a35tcsg324-1。只做行为仿真。
本轮增加 FWFT 独立参考模型、7 组回归和 18432 组参数，不全跑大矩阵。
加上原有标准读，FIFO 共 10 组回归、19584 组大矩阵参数。

## 检查方法

根据 [PG057](https://docs.amd.com/api/khub/documents/Ds0JjAYlvIFpRMxJMOrbRw/content)
的 FWFT 读模式、实际深度和延迟表建模，没有从厂商仿真代码复制参考模型。
模型以写入周期确定首字和标志何时有效，检查额外两项容量、输出保持和数据顺序。
只屏蔽无有效数据时的 dout，八个状态和握手标志每拍都比较。

定向序列包含全部 1024 种五拍读写控制组合、两轮满空、指针回绕及首字前后复位。
这是有限控制序列检查，不是完整状态空间或数据历史的穷举。

## 真实 IP 回归

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type fifo_generator
```

编号 `2026-09-15_06-33-25_UTC+0800_34afcac3`，10 组配置的 30 个阶段全部 PASS。
包括 1 位、8 位、17 位、33 位、256 位，两种存储，标志高低有效和不同复位值。
两个 256 位、4096 深度的 FWFT 分别比较 61551 和 59511 拍。
全批共比较 217088 拍，243 份源码和 634 个归档产物的哈希核对一致。
这些结果只表示本批没有发现差异，不代表完整参数空间都通过。

旧标准读三组的输入、期望值、掩码、向量和周期 JSON 共 15 个文件，与
`2026-09-14_23-18-33_UTC+0800_8757ceec` 逐字节一致。
调度 JSON 只有后来新增的 `fully_masked_cycles: 0` 字段不同。

## 检查器和独立对照

```bash
VIVADO_INTEGRATION=1 PYTHONPATH=src:tests python3 -m unittest \
  integration.ip.fifo_generator.test_failure_detection -fv
```

两项测试共运行 13 次 XSim，耗时约 205 秒：正确替身通过，11 种人为错误均被检测到，
另一个真实 IP 的固定输入输出对照通过。固定期望值不调用 Python FIFO 模型。
人为错误包含错数、提前 valid、停读时输出变化、八个标志错误及有效数据中的 X，
其中提前 valid 也是八个标志检查之一。这些不计作 AMD IP bug。

替身日志位于 `runs/logs/framework/failure_detection/` 下，编号从
`2026-09-15_06-31-20_UTC+0800_2fab7ab5` 至 `2026-09-15_06-34-09_UTC+0800_65085190`，
子目录为 `fifo_generator/fwft_<错误类型>/`。
固定对照编号为 `2026-09-15_06-34-25_UTC+0800_7f6e64f7`，位于
`runs/logs/framework/protocol_probe/<编号>/fifo_generator/fwft_literal/`。

## 框架检查

`python3 -m py_compile scripts/run_all.py` 通过。
完整 unittest 共 482 项，334 项通过、148 项真实工具测试按规则跳过，耗时约 199 秒。
所有 593046 组扩展参数均完成独立性和插件约束检查，没有把它们都交给 Vivado 运行。
`scripts/run_all.py` 和原有 Divider demo Tcl 没有修改。

最后执行不带选项的 `python3 scripts/run_all.py`，编号
`2026-09-15_06-37-13_UTC+0800_b786fc70`，默认六组、19 个阶段全部 PASS。
243 份源码和 481 个归档产物的哈希核对一致。
公共测试辅助代码补充掩码支持后，另复跑 Inline 向量逻辑的正确替身和未知位检查，
两项均符合预期，耗时约 30 秒；原有无掩码检查仍正常。

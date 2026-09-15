# FIFO 计数与阈值接入检查

2026-09-15，Vivado 2025.2，器件 xc7a35tcsg324-1。只做行为仿真。
本轮增加 data_count、常量单阈值和滞回阈值，支持标准读和 FWFT。
参考模型按已接受的读写计数，不读取 DUT 输出生成期望值。
规则及手册歧义见[计数与阈值](../ip/fifo_generator/status_protocol.md)。

## 新增范围

FIFO 新增 14 组常用回归、161808 组不同参数，总计 24 组回归、181392 组大矩阵参数。
宽度范围扩大到 1 至 1024 位，深度为 16 至 131072 的二次幂。
配置按计数、单阈值和滞回阈值分目录，阈值输入端口尚未接入。

大矩阵覆盖各深度的全部可用计数位宽。深度 16 的单阈值覆盖合法 full/empty 组合；
滞回配置分别覆盖每个合法的 full 阈值对和 empty 阈值对，不是两者的完整交叉乘积。
较大深度选择最小值、中间值和最大值附近的阈值。
归一化默认参数后，181392 组没有重复，全部通过插件约束检查。
这些是可选配置，不是已经完成的仿真次数。

## 真实 IP 回归

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --config configs/ip/fifo_generator/regression/status.json
```

编号 `2026-09-15_06-54-11_UTC+0800_ba328f2d`，14 组、42 个阶段全部 PASS。
共比较 3565721 拍，244 份源码和 791 个归档产物的哈希核对一致。
两组 1024 位配置比较 82029、96699 拍；两组 131072 深度配置比较
1573147、1390830 拍。还包含窄计数、单独启用一个阈值标志、
两种存储、握手标志高低有效和不同复位值。
计数及阈值标志每拍都比较，只有规范未定义的数据输出使用掩码。
本批未发现 IP 行为差异，不代表所有参数都通过。

旧配置对照编号 `2026-09-15_07-03-47_UTC+0800_37407859`：
`fifo_block8`、`fifo_fwft_dist17_low` 的六个阶段全部 PASS。
每组的六份向量文件与 `2026-09-15_06-33-25_UTC+0800_34afcac3` 逐字节一致。
本批 244 份源码和 323 个归档产物的哈希核对一致。

## 检查器和固定对照

```bash
VIVADO_INTEGRATION=1 PYTHONPATH=src:tests python3 -m unittest \
  integration.ip.fifo_generator.test_status_detection \
  integration.ip.fifo_generator.test_failure_detection.FwftFailureDetectionTests.test_real_ip_matches_literal_trace_without_python_reference -fv
```

四项测试通过，共运行十次 XSim，约 166 秒。正确替身通过，六种人为错误均被检出：
错误计数、提前 full、延后 empty、计数中的未知位、延后计数和复位计数残留。
这些是检查器测试，不计作 AMD IP bug。

另外三次是真实 IP 的固定输入输出对照，期望值不调用 Python 队列模型：

| 对照 | 运行编号 |
| --- | --- |
| FWFT 计数及首字等待 | `2026-09-15_06-54-57_UTC+0800_1d046d5a` |
| 标准读计数及阈值延迟 | `2026-09-15_06-55-16_UTC+0800_f891b390` |
| 原有 FWFT 固定序列 | `2026-09-15_06-55-36_UTC+0800_95a851d8` |

固定对照位于 `runs/framework/protocol_probe/<编号>/fifo_generator/`，
日志在对应的 `runs/logs/framework/protocol_probe/`。
三组的输入、期望值、掩码和 testbench 哈希均已复核。

## 框架检查

`python3 -m py_compile scripts/run_all.py` 通过。
完整 unittest 共 492 项，341 项通过、151 项真实工具测试按规则跳过，耗时约 442 秒。
全部 754854 组扩展参数完成配置及插件检查，没有全量运行 Vivado。
`scripts/run_all.py` 和原有 Divider demo Tcl 没有修改。

最后执行不带选项的 `python3 scripts/run_all.py`，编号
`2026-09-15_07-04-52_UTC+0800_b95bf6f5`，默认六组、19 个阶段全部 PASS。
244 份源码和 482 个归档产物的哈希核对一致。

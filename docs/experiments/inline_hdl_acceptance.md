# Inline HDL 接入检查

2026-09-15，Vivado 2025.2。只运行行为仿真，没有综合、实现或网表仿真。

新增 ilconcat、ilslice、ilconstant 的独立配置、参考模型、创建入口和故障检测测试。
全工程现有 30 类 IP、173 组常用参数；可选大矩阵为 545830 组不同参数。
本轮增加 58852 组，但没有全量运行大矩阵。

## 实际运行

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type ilconcat --ip-type ilslice --ip-type ilconstant
```

编号 `2026-09-15_05-44-28_UTC+0800_a35c187c`，21 组配置、63 个阶段全部 PASS。

| 模块 | 实测配置数 | 包含的边界 |
| --- | ---: | --- |
| ilconcat | 6 | 单路 1 位、混合宽度、128 路、首尾各 4096 位 |
| ilslice | 7 | 单位截取、第 4095 位、跨第 256 位、完整 4096 位 |
| ilconstant | 8 | 零和一、四种写法、4096 位最高位和十进制全一 |

完整 4096 位截取实际比较 8475 行；128 路单比特拼接比较 2065 行。
每个常量观察 64 次，没有虚构输入事务。
归档核对了 233 份源码和 1056 个产物哈希，均一致；其中包含 21 份 `.bd` 和 21 份行为 HDL。

此前首批 4 组的编号为 `2026-09-15_05-42-13_UTC+0800_ba8002ea`，12 个阶段通过。
该批尚未补齐 `.bd` 的独立归档，因此以后一批作为接入验收记录，不改写旧记录。

## 最大宽度拼接

```bash
python3 scripts/run_all.py --config configs/ip/ilconcat/extended.json \
  --case ilconcat__input_widths_n128_w4096
```

编号 `2026-09-15_05-53-08_UTC+0800_b22e4aab`，三个阶段全部 PASS。
128 路各 4096 位，输出为 524288 位；2048 个生成输入加逐位标识序列和收尾，共比较 2089 行。
创建约 19.45 秒，生成输入和 testbench 约 13.58 秒，仿真阶段约 74.20 秒。
实际输出哈希为 `8828990afc3acc6669b1542b740da53d450634054d82d1257d326454c9edbf96`。
233 份源码和 273 个归档产物的哈希均核对一致。

## 检查器能否报错

```bash
VIVADO_INTEGRATION=1 PYTHONPATH=src:tests python3 -m unittest \
  integration.ip.ilconcat.test_failure_detection \
  integration.ip.ilslice.test_failure_detection \
  integration.ip.ilconstant.test_failure_detection -fv
```

12 项真实 XSim 检查全部符合预期，耗时约 184 秒。
正确替身通过；接反端口、偏移一位、混入未选位、丢高位、未知位和延迟改变常量均被检测到。
这些是人为制造的错误，用来检查框架，不是发现了 9 个 AMD IP bug。

## 离线检查

```bash
python3 -m py_compile scripts/run_all.py
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
```

451 项测试中 314 项通过，137 项真实工具测试按规则跳过，总耗时约 183 秒。
包含完整矩阵的参数、预算和重复检查，以及 `.bd` 参数、端口、接线和归档检查。

最后运行不带选项的 `python3 scripts/run_all.py`，编号
`2026-09-15_05-55-34_UTC+0800_f64b0f8b`，原有 6 组配置、19 个阶段全部 PASS，
包括 Divider 官方 demo 和 Divider/Multiplier 数值自检。

PASS 只说明这些测试没有发现异常。旧版 xlconcat 的 128 路异常仍保留，
不能因为新版通过就删除旧版失败，也不能把旧版问题算作新版 bug。

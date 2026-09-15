# 连接工具接入记录

2026-09-15，Vivado 2025.2，均为行为仿真。
新增旧版 xlconcat、xlslice、xlconstant；全工程为 27 类 IP、152 组常用配置。
大矩阵合计 486978 组，只做配置校验，不把它当作全部通过的测试结果。

| 类型 | 常用配置 | 可选矩阵 |
| --- | ---: | ---: |
| xlconcat | 6 | 15014 |
| xlslice | 6 | 61580 |
| xlconstant | 8 | 17161 |

## 真实 IP 回归

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type xlconcat --ip-type xlslice --ip-type xlconstant
```

批次 `2026-09-15_04-59-48_UTC+0800_453f0aae` 完成 60 个阶段，58 PASS、2 SIMULATION_FAILED。
失败都是旧版拼接的 128 路配置；其余 18 组全部通过。
切片包括 4096 位输入和第 255 位；常量包括四种写法、4096 位最高位和全 1。
报告位于 `reports/history/<编号>/`，218 个源码哈希和 984 个归档文件哈希已核对一致。

128 路异常已用独立 VHDL、127 路对照、Inline HDL 对照和直接编译源模型检查，
见[问题记录](../ip/xlconcat/port_128_issue.md)。不修改期望值来取得 PASS，
也不把两组触发算成两个 bug。旧版已被提示弃用，新版的对照正常。

## 框架检查

```bash
python3 -m py_compile scripts/run_all.py
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
VIVADO_INTEGRATION=1 PYTHONPATH=src:tests python3 -m unittest \
  integration.ip.xlconcat.test_failure_detection \
  integration.ip.xlslice.test_failure_detection \
  integration.ip.xlconstant.test_failure_detection \
  integration.test_cycle_failure_detection \
  integration.test_masked_failure_detection -v
```

完整测试发现 414 项，289 项通过、125 项需要显式启用 Vivado 的测试跳过。
读取器修改后另跑了 26 项真实 XSim 检查，均符合预期：正常对照通过，故障和非法行被拒绝。
覆盖端口接反、位错接、丢位、未知值、有效位掩码，以及常量在 300 ns 后改变。
这些是人为故障，用于检查框架，不属于发现的 IP bug。
矩阵另检查参数去重、所有端口数/输入宽度，以及常量不同写法不能重复计数。

## 超宽对照

独立 VHDL 批次 `2026-09-15_05-13-44_UTC+0800_ba9f6aed` 使用 127 路、每路 4096 位，
输出共 520192 位。六种输入模式均匹配，创建和仿真总计约 36 秒。
完整文件自检的输入数量更多，不能直接用两次总耗时计算提速倍数。
完整文件测试的首轮批次为 `2026-09-15_05-08-46_UTC+0800_0dc6ec8e`：
创建和生成均通过，仿真在 600 秒后超时，已完成的 164 次比较均匹配。
这是框架读取宽文本的性能问题，不是已经观察到 IP 数值错误。

公共检查器改为按下标读取整行二进制字符，同时拒绝长度不符和非二进制字符。
首版声明曾触发 VHDL 访问类型参数错误，失败保存在
`2026-09-15_05-20-49_UTC+0800_56f05165`，随后已修复；这也是框架问题。
修复后的 `2026-09-15_05-22-56_UTC+0800_d63f9f90` 三阶段全部通过：
同样的 1024 组输入加 40 次位模式和一次刷新，共 1065 次比较，仿真阶段约 42 秒。
输入、期望值和调度未改，旧版 128 路问题也没有被回避。
前后五份输入及调度文件的哈希相同；修复批次的 218 个源码哈希和 257 个归档文件哈希一致。

随后批次 `2026-09-15_05-25-34_UTC+0800_5d6e44a9` 补跑计数器、两种块存储器、
宽切片、无输入宽常量和旧版 128 路拼接，共 18 阶段，17 PASS、1 SIMULATION_FAILED。
唯一失败仍是旧版 128 路拼接。有时钟、有效位掩码和无输入接口均通过。

最后执行 `python3 scripts/run_all.py`，批次
`2026-09-15_05-28-30_UTC+0800_b298fc05` 的默认六组配置、19 个阶段全部通过。
这不覆盖整个大矩阵，也不改变前面保留的失败结论。

# 架构说明

## 一次运行

入口是 `scripts/run_all.py`，实际代码在 `src/vivado_ip_test/`。

```text
读取并校验配置
  -> 按 ip_type 选择插件
  -> create_ip
  -> sim_demo（配置启用时）
  -> generate_testbench
  -> sim_selfcheck
  -> 保存报告和归档
```

`generate_testbench` 包括 XCI 解析、选取输入、计算期望值和生成 VHDL。
`sim_selfcheck` 包括 XSim 仿真和 Python 输出文件复核；
它们不是另行列出的报告阶段。

一个阶段失败后，该配置的后续阶段不再执行，其他配置继续运行。
报告只记录实际执行的阶段。配置错误在启动 Vivado 前退出。

## 各模块做什么

| 模块 | 工作 |
| --- | --- |
| `application/` | 命令行参数、服务组装和阶段顺序 |
| `configuration/` | 加载配置、合并引用、展开种子和时序组合 |
| `domain/` | 配置、请求、生成文件和阶段结果的数据结构 |
| `services/` | 创建 IP、生成 testbench、仿真、报告、归档和续跑 |
| `plugins/<ip_type>/` | 某类 IP 的参数、端口、参考模型和模板 |
| `strategies/` | 从合法输入中选择测试数据 |
| `adapters/vivado/` | 组织 Vivado batch 调用 |
| `infrastructure/` | 进程执行、目录、时间编号、锁和哈希 |

完整路径见[目录说明](directory_structure.md)。

## 公共入口

应用层调用以下接口：

```python
ip_builder.build(case)
testbench_generator.generate(case)
simulation_runner.run(case, stage)
recorder.capture(result)
```

`IpBuilder`、`TestbenchGenerator` 和 `SimulationRunner` 都通过
`PluginRegistry` 选择具体 IP。目前只有 Divider 和 Multiplier 两个插件。
同类 IP 的不同参数共用模板；不同 IP 的端口和计算规则由各自插件处理。

`SimulationRunner` 使用 `tcl/run_xsim_batch.tcl` 生成 XSim 脚本，
再依次编译、展开和运行。仿真成功后，插件复核输出文件。

`RunRecorder` 每阶段保存报告和关键文件，`ReportGenerator.write_bundle()`
负责写 CSV、JSON 和分 IP 报告。工作工程、日志和归档共用一个时间编号。
同一工作区只允许一个运行任务；超时会清理整组 Vivado/XSim 子进程。

## 算法和判定

插件通过 `CaseSpace` 提供合法输入、边界和覆盖分类。
`StrategyRegistry` 按策略名称和版本选择输入，策略不接触 Vivado。

Python 参考模型计算期望值，HDL testbench 比较实际输出。
仿真后的 Python 复核使用同一份期望文件，不是第二个独立模型。
Divider 还检查输出有效信号的时序；Multiplier 按 XCI 时延采样。

当前测的是 IP 行为仿真模型，不包括综合后、布局布线后或 FPGA 板级测试。

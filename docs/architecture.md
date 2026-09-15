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

`generate_testbench` 包括 XCI 或 Inline HDL `.bd` 解析、选取输入、计算期望值和生成 VHDL。
`sim_selfcheck` 包括 XSim 仿真和 Python 输出文件复核；
它们不是另行列出的报告阶段。

一个阶段失败后，该配置的后续阶段不再执行，其他配置继续运行。
报告只记录实际执行的阶段。配置错误在启动 Vivado 前退出。
配置通过 `iter_test_cases()` 逐项读取，应用层完整扫描并校验后，只保留本次要执行的配置。
小规模名称去重在内存中完成，超过上限转为临时 SQLite 索引；不把整个大矩阵留在列表中。
原有 `load_test_cases()` 仍返回列表，供确实需要完整小配置的调用方使用。
续跑证据先核对源码和文件哈希，再按完整配置匹配；`--limit` 不改变这些条件。

## 各模块做什么

| 模块 | 工作 |
| --- | --- |
| `application/` | 命令行参数、服务组装和阶段顺序 |
| `configuration/` | 加载配置、合并引用、展开参数轴；种子和时序展开为可选项 |
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
`PluginRegistry` 选择具体 IP，注册表位于 `plugins/catalog.py`。
同类 IP 的不同参数共用模板；不同 IP 的端口和计算规则由各自插件处理。
简单组合、单时钟 IP 共用 `plugins/common/` 的逐周期后端，参数和参考模型仍按 IP 分开。
需要 IP Integrator 的连接工具由公共 batch Tcl 创建单核 Block Design，
仍通过 IpBuilder 和同一仿真入口运行。旧版插件明确给出内部 XCI 路径，不靠任意文件匹配。
Inline HDL 插件则明确给出 `.bd` 路径，检查模块标识、参数、端口方向/上下界及直连关系。
缺少 `.bd` 记为 BLOCK_DESIGN_NOT_FOUND；旧版 XCI_NOT_FOUND 分类不变。
清单中的产物名称区分 xci 与 block_design，归档另保存生成的行为 HDL。
无输入常量使用同一个检查器，但不生成虚假的输入端口，指标区分输出观察和输入事务。
逐周期后端的向量文本按整行下标读取，严格检查二进制字符和宽度，避免超宽行逐字符消耗的开销。
超宽输入的 JSON 副本和覆盖标签改用可还原的十六进制字符串，不改变计算和仿真的二进制数据。
透传流接口共用 `plugins/common/stream/`，按握手检查，不用固定延迟逐周期比较。
它不是第二个公共入口，外层仍只调用 `TestbenchGenerator`。
AXI-Lite 使用 `plugins/common/axilite/`，驱动总线请求、响应和回压；
各外设分别提供寄存器状态模型和操作序列，目前接入 GPIO 和 Timer。
Timer 使用可选计数窗口和单周期脉冲观察，不把自由运行计数器当作普通 GPIO 寄存器处理。

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
逐周期后端先排好定向序列、输入顺序和间隔，再计算状态变化。
存储类插件可预先标出没有确定期望值的位，参考模型与实际 DUT 输出互不依赖。
掩码和原因随输入归档，未屏蔽的位仍严格比较，详见[有效位规则](protocols/defined_output_bits.md)。
时序 IP 在上升沿后采样，组合 IP 在输入稳定后采样；复位、暂停和刷新周期也要比较。
完整输入历史保存在 `cycles.json`。失败周期的输入不一定是造成错误的那笔事务。
流接口另存实际接收的输入、输出握手历史和暂停计数，结束前再检查多余输出。
检查细节和未覆盖情况见 [AXI-Stream 自检](protocols/axis_stream.md)。
AXI-Lite 每行对应一次寄存器访问、引脚变化、复位或计数窗口，另保存实际总线握手日志。
状态错误可能来自前面的操作，失败记录带前八次操作和最近一次复位的位置，
不把报错位置当成已经找到的根因。详见 [AXI-Lite 自检](protocols/axi_lite.md)。

当前测的是 IP 行为仿真模型，不包括综合后、布局布线后或 FPGA 板级测试。
这就是项目的测试范围，不是等待补上的阶段。不要加入综合、实现或网表仿真。
`generate_target` 生成 IP 的仿真模型，`xvhdl/xvlog` 编译、`xelab` 展开后交给 XSim；
这些步骤不会运行 `synth_design`，也不使用综合后网表作测试对象。

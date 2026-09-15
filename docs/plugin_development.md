# 新增 IP 插件

插件保存某类 IP 的参数、端口、计算规则和 testbench 模板。
公共流程只按 `ip_type` 调用插件，不按用例名称判断类型。

## 文件位置

```text
src/vivado_ip_test/plugins/<ip_type>/
  plugin.py
  metadata.py
  reference.py
  vectors.py
  testbench.py
  templates/tb_<ip_type>_selfcheck.vhd.tpl
configs/ip/<ip_type>/
configs/schemas/ip/<ip_type>/
tcl/ip/<ip_type>/create_ip.tcl
tests/unit/plugins/<ip_type>/
docs/ip/<ip_type>/
```

产物路径统一从 `RepositoryLayout` 获取，使用本批时间目录。
不要在插件里另设输出目录或复制一套总控脚本。

简单的组合或单时钟 IP 可以继承 `CycleIpPlugin`，只提供 `describe(parameters)`
和独立参考模型。`CycleSpec` 描述端口、Vivado 参数、模型参数、初始状态和定向序列。
这样只需 `plugin.py`、`reference.py`，不必复制元数据解析、文件读写和 VHDL 模板。
长地址扫描可用惰性的 prefix/suffix，避免配置检查时生成全部数据。
若规范确实存在不确定位，需显式启用 masked_outputs 并返回带原因的 DefinedBits。
不能为了让测试通过而忽略整类输出；规则见[有效位比较](protocols/defined_output_bits.md)。
透传 AXI-Stream IP 可使用 `StreamIpPlugin`，提供 `StreamSpec` 和事务参考模型。
它共用驱动和握手检查，不能用逐周期后端代替。不透传的 IP 需要补充转换规则，
不能直接照搬“输入等于输出”的模型。
广播器通过公共流后端的 `renderer`、`sink_pattern` 扩展点提供多支路模板和独立回压。
物理端口布局与参考文件布局分别描述，仍由公共入口保存输入、参考和哈希。
这不改变插件对外接口，也不能把广播器的组合通路约束套到带缓冲的路由器。
汇合器通过 `source_timing` 提供每组每路的间隔，通过 `renderer` 生成多输入驱动。
没有提供该扩展时，原有单输入的间隔文件和驱动方式不变。
交换器的 `SwitchTestbenchBackend` 负责独立输入、路由队列、逐路文件和结果合并，
仍通过同一个 TestbenchGenerator 调用，共用 IP 创建、XSim 执行和归档服务。
它不等待一组所有输入完成才发下一组，也不规定不同输出的全局顺序。
在 `plugins/catalog.py` 注册，并增加本 IP 的参数 schema 引用。
AXI-Lite 寄存器外设可以继承 `AxiLiteIpPlugin`，提供 `AxiLiteSpec`、操作序列和状态模型。
公共后端只管总线握手与文件；寄存器地址、访问副作用和引脚规则留在本 IP 目录。
有自由运行计数器的外设不能直接沿用 GPIO 的“每次操作后采样”模型，必须计算经过的时钟数。

## 实现顺序

1. 用 Vivado batch 创建代表配置，读取 XCI、仿真封装和官方说明，确认端口、位宽、符号、时延和复位规则。
2. 在参数 schema 和插件中写入约束；解析 XCI 后核对实际参数。
3. 写不依赖 Vivado 的参考模型，并测试边界值。
4. 定义 `CaseSpace`，提供合法输入、边界、遍历方法和覆盖分类。
5. 通过 `StrategyRegistry` 选择输入，生成期望文件和自检 testbench。
6. 注册插件，加入配置，运行单元测试和真实 XSim 测试。

## 插件接口

```python
class IpPlugin:
    ip_type: str

    def validate_case(self, case): ...
    def build_request(self, case): ...
    def generate_testbench(self, case): ...
    def simulation_request(self, case, stage): ...
    def verify_simulation(self, case, stage): ...
```

`BuildRequest` 提供创建 Tcl、参数、日志路径、成功标记和 XCI 查找规则。
`IpBuilder` 负责调用 Vivado，并处理超时、日志缺失和创建失败。

`generate_testbench` 生成输入、期望值、HDL、`vectors.json` 和 `manifest.json`。
位宽、输出布局和时延要与 XCI 核对，不能从 `case_id` 推断。

`SimulationRequest` 提供工程、testbench、top 和结果标记。
`SimulationRunner` 经公共 Tcl 编译并运行 XSim，然后调用
`verify_simulation` 复核文件。若 testbench 用 `severity failure` 正常结束，
需依据实际成功/失败标记判断，不能只看 XSim 返回码。

## 接入检查

至少有一组配置完成真实创建和自检，报告能追溯到参数、策略、输入和输出。
单元测试应覆盖参数、参考模型、输入空间和错误判定，且不依赖 Vivado。

另用故意出错的 DUT 检查 testbench 能否报错并保存首个错误值。
这种故障注入是测试框架的方法，不算真实 IP bug。
不能仅凭实测输出修改参考模型；规范不明确的地方应单独记录并保留原始证据。

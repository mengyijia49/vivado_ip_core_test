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

# 目录说明

公共代码按工作内容划分，IP 专属文件按 `ip_type` 划分。
不同 IP 不共用参数文件；公共入口用 `includes` 引用各自配置。

## 源码和配置

```text
configs/
  ip_matrix.json                   默认回归入口
  bug_discovery.json               缺陷探索入口
  extended_regression.json         全部 IP 的常用回归
  extended_discovery.json          可选的大参数矩阵
  ip/<ip_type>/                    regression.json、extended.json 等
  schemas/ip_matrix.schema.json    公共格式
  schemas/ip/<ip_type>/            参数格式
src/vivado_ip_test/
  application/                     命令行和流水线
  configuration/                   配置加载
  domain/                          数据结构
  services/                        创建、生成、仿真、记录等公共服务
  strategies/                      输入选择算法
  plugins/<ip_type>/               IP 模型、模板和实现
  plugins/common/                  共用逐周期后端，不放具体 IP 参数
  plugins/common/stream/           共用流接口驱动和检查，不放具体 IP 参数
  plugins/catalog.py              插件注册表
  adapters/vivado/                 Vivado 调用
  infrastructure/                  进程、路径、锁等工具
tcl/
  run_xsim_batch.tcl               公共仿真入口
  shared/                         通用 IP 创建步骤
  diagnostics/                    工具诊断
  ip/<ip_type>/                   IP 创建和专属诊断
tests/
  unit/                           公共单元测试
  unit/plugins/<ip_type>/          IP 单元测试
  integration/                    集成测试
  integration/ip/<ip_type>/        新增 IP 的集成检查
  fixtures/ip/<ip_type>/           故障注入模块
docs/
  ip/<ip_type>/                   IP 参数、协议和自检说明
  protocols/                      多类 IP 共用的接口检查说明
  experiments/                    历史实验记录
  history/                        早期原型文本
scripts/
  run_all.py                      统一入口
  maintenance/                    维护工具
```

`tcl/ip/divider/run_demo_sim.tcl` 是保留的早期脚本，正式流水线不再调用它。
早期 Python 原型保存为 `docs/history/` 下的文本，不提供另一套运行入口。

同一 IP 功能较多时继续拆子目录。例如 `plugins/floating_point/` 的 `compare/`
负责比较，`arithmetic/` 负责加减和乘法，`divide/` 负责除法，
`multi_input/` 放共用输入驱动、侧带和模板。
对应参数分别保存在 `configs/ip/floating_point/regression/` 和 `matrices/` 的运算文件中。
顶层生成、仿真接口不变，不要求使用者手动选择内部模板。

## 每次运行的文件

运行编号使用本地时间，例如 `2026-09-22_20-55-03_UTC+0800_a1b2c3d4`。
前半部分是日期、时分秒和 UTC 偏移，后缀用于避免同秒重名。
同一批的工程、日志和报告使用相同编号。

```text
runs/
  batches/<vivado_version>/<run_id>/<ip_type>/<case_id>/
    proj/                          完整 Vivado 工程
    tb/                            生成的自检 testbench
    vectors/                       输入、期望值和时序映射
    outputs/                       实际输出，失败时的 failure.json
    work/<stage>/                  阶段临时文件
    manifest.json
  history/<vivado_version>/<run_id>/
    source/                        Python、Tcl 和模板快照
    ip_matrix.json                 本次有效配置
    configs/<ip_type>/              多 IP 运行的分文件配置
    cases/<ip_type>/<case_id>/      关键文件副本
  logs/
    batches/<vivado_version>/<run_id>/<ip_type>/<case_id>/
    history/<vivado_version>/<run_id>/<ip_type>/<case_id>/<stage>/
    framework/<用途>/<run_id>/      框架自测日志
  framework/<用途>/<run_id>/         框架自测产物
reports/
  history/<vivado_version>/<run_id>/
    report.csv
    report.json
    run.json                       状态、哈希和复现命令
    ip/<ip_type>/                  分 IP 报告
  latest -> history/<vivado_version>/<run_id>  最近启动的一批
  by_version/<vivado_version>/latest -> ../../history/<vivado_version>/<run_id>
  maintenance/<run_id>/             维护记录
  framework/<用途>/<run_id>/         框架自测与资源测量报告
```

每次运行都新建目录，不覆盖旧工程。仿真内部日志仍留在 Vivado 要求的位置，
归档时另存到日志目录。目录名已有时间，里面的文件不必重复加时间。

`reports/latest` 只改链接，不保存第二份无日期报告。
每版本的 `latest` 链接也不复制报告。
所有路径由 `RepositoryLayout` 生成，插件不要自行拼出另一套目录规则。

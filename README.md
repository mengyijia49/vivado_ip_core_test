# Vivado IP 核自动测试框架

[![Python 单元测试](https://github.com/mengyijia49/vivado_ip_core_test/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/mengyijia49/vivado_ip_core_test/actions/workflows/unit-tests.yml)

这个项目用于寻找 Vivado IP 核的潜在缺陷。Python 生成测试输入和期望值，
再调用 Vivado batch 创建 IP、运行 XSim，并保存结果，全程不需要 GUI。
只做行为仿真（功能仿真），不运行综合、实现、网表仿真或时序仿真。
XSim 的编译和展开是启动仿真的准备，不是综合。

目前接入 36 类 IP。常用回归有 323 组参数，可选的大矩阵有 9472890 组不同参数。
大矩阵不默认运行，也不自动乘上多个种子和时序模式。
`PASS` 表示本批测试没有发现异常，不代表 IP 没有 bug。
其中 xlconcat、xlslice、xlconstant 是旧版连接工具，Vivado 已提示迁移到 Inline HDL；
Inline 拼接、截取、常量、向量逻辑和归约逻辑已分别接入自检和独立配置。
旧版的测试结果不算到替代模块上。

## 开始运行

已验证环境为 Ubuntu、Vivado 2025.2、Python 3.10 或更高版本。
在仓库根目录执行：

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type divider
python3 scripts/run_all.py --all
```

第一条测试某类 IP，第二条测试全部 IP 的常用配置；按需要选一条。
支持的类型和参数范围见 [IP 清单](docs/ip/catalog.md)。
不带选项仍运行原有六组配置，兼容之前的用法。

查看待测配置，或只测某一组参数：

```bash
python3 scripts/run_all.py --all --list-cases
python3 scripts/run_all.py --all --case counter_updown_control
```

需要更多参数时才选择大矩阵，例如只跑计数器的前 3 组：

```bash
python3 scripts/run_all.py --config configs/extended_discovery.json --ip-type counter --limit 3
```

同一参数、输入和时序不必反复测试。分批运行或重现异常时再用历史记录，
方法见 [复现和续跑](docs/reproducibility.md)。
已有异常的复现证据和剩余疑点见[待确认问题](docs/experiments/bug_candidates.md)。
可提交到 GitHub 的小证据包见[公开证据](evidence/README.md)。
其中 INTC 已接入寄存器、中断状态和握手自检，ISR 与 ME 的异常另有独立复现。
`--all` 会保留已接入 IP 的失败结果，不会自动跳过或改成 PASS。

## 流程和结果

1. 读取配置，创建对应参数的 IP。
2. 读取 XCI 或 Inline HDL 的 `.bd`，核对实际配置、接口和适用的时延。
3. 选择输入，用 Python 参考模型算出期望值，生成自检 testbench。
4. XSim 运行 IP 仿真模型，testbench 逐项比较结果，Python 随后复核输出文件。
5. 保存报告；失败时保留首条差异，并按阶段和字段汇总后续差异，供复现和排查。

只有 `divider_u16_u8` 额外运行官方 demo。它检查有效输出中的未知值，
不比较商和余数；数值检查由框架生成的自检 testbench 完成。

每次运行使用本地时间编号，例如 `2026-09-14_20-55-03_UTC+0800_a1b2c3d4`。
编号含日期、时分秒、时区和随机后缀，同一分钟重跑也不会覆盖旧文件。

| 内容 | 位置 |
| --- | --- |
| 完整工程、输入输出 | `runs/batches/<run_id>/<ip_type>/<case_id>/` |
| 阶段日志 | `runs/logs/batches/<run_id>/<ip_type>/<case_id>/` |
| 源码、配置与关键文件归档 | `runs/history/<run_id>/` |
| 归档日志 | `runs/logs/history/<run_id>/` |
| 报告和复现命令 | `reports/history/<run_id>/` |

`reports/latest` 是最近一批报告的符号链接。先看 `report.csv`；
要确认整批完成，再看 `run.json` 的 `state` 和 `outcome`。
完整工程会逐批保留，长期测试前请预留磁盘空间。

## 文档

- 使用：[配置格式](docs/configuration.md)、[缺陷探索配置](docs/bug_discovery.md)、[异常排查](docs/bug_hunting.md)。
- 结果：[报告格式](docs/report_format.md)、[复现方法](docs/reproducibility.md)、[XSim 排查记录](docs/xsim_runtime_issue.md)。
- IP：[支持范围和运行命令](docs/ip/catalog.md)，各类 IP 的说明按目录保存。
- 开发：[目录说明](docs/directory_structure.md)、[架构](docs/architecture.md)、[生成策略](docs/test_generation_strategies.md)、[新增插件](docs/plugin_development.md)。
- 检查与计划：[验收清单](docs/framework_acceptance.md)、[历史验收记录](docs/experiments/bug_discovery_acceptance.md)、[后续工作](docs/roadmap.md)。

开发检查见[贡献指南](CONTRIBUTING.md)。项目使用 [MIT 许可证](LICENSE)。

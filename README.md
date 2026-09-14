# Vivado IP 核自动测试框架

[![Python 单元测试](https://github.com/mengyijia49/vivado_ip_core_test/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/mengyijia49/vivado_ip_core_test/actions/workflows/unit-tests.yml)

这个项目用于寻找 Vivado IP 核的潜在缺陷。Python 生成测试输入和期望值，
再调用 Vivado batch 创建 IP、运行 XSim，并保存结果，全程不需要 GUI。

目前支持 Divider Generator 和 Multiplier Generator。默认回归有 6 组参数、
238 个输入对，共 19 个阶段。缺陷探索配置另有 90 个实验，适合分批运行。
`PASS` 表示本批测试没有发现异常，不代表 IP 没有 bug。

## 开始运行

已验证环境为 Ubuntu、Vivado 2025.2、Python 3.10 或更高版本。
在仓库根目录执行：

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py
```

查看配置，或只测一组参数：

```bash
python3 scripts/run_all.py --list-cases
python3 scripts/run_all.py --case multiplier_u8_u8 --seed 42 --budget 200
```

开始较大规模的探索，先跑 3 个实验：

```bash
python3 scripts/run_all.py --config configs/bug_discovery.json --limit 3
```

## 流程和结果

1. 读取配置，创建对应参数的 IP。
2. 读取 XCI，核对实际位宽和时延。
3. 选择输入，用 Python 参考模型算出期望值，生成自检 testbench。
4. XSim 运行 IP 仿真模型，testbench 逐项比较结果，Python 随后复核输出文件。
5. 保存报告；出现差异时保留输入、输出和日志，供复现和排查。

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
- IP：[Divider 自检](docs/ip/divider/selfcheck.md)、[Multiplier 自检](docs/ip/multiplier/selfcheck.md)。
- 开发：[目录说明](docs/directory_structure.md)、[架构](docs/architecture.md)、[生成策略](docs/test_generation_strategies.md)、[新增插件](docs/plugin_development.md)。
- 检查与计划：[验收清单](docs/framework_acceptance.md)、[历史验收记录](docs/experiments/bug_discovery_acceptance.md)、[后续工作](docs/roadmap.md)。

开发检查见[贡献指南](CONTRIBUTING.md)。项目使用 [MIT 许可证](LICENSE)。

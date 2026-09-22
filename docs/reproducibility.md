# 复现方法

## 环境

以后使用 Ubuntu、Vivado 2026.1、Python 3.10 或更高版本。
2026.1 已完成 478 组常用配置。目标器件为 `xc7a35tcsg324-1`。
实际版本、修订号和参数以每个配置的 `manifest.json` 为准。

默认回归命令见 [README](../README.md)。
应有 6 组配置、19 条阶段记录，其中 2 位无符号乘法器穷举全部 16 个输入对。

## 保存了什么

每批有统一时间编号，文件位置见[目录说明](directory_structure.md)。

- 工作目录保留完整 Vivado 工程、生成的 testbench、输入和输出。
- `runs/history/<vivado_version>/<run_id>/` 保存有效配置、源码快照和关键文件副本。
- `runs/logs/history/<vivado_version>/<run_id>/` 保存已完成阶段的日志副本。
- `reports/history/<vivado_version>/<run_id>/run.json` 保存版本、阶段、哈希和复现命令。

`manifest.json` 记录配置和 XCI 实际参数、工具版本、策略和向量信息。
归档副本里的原始路径指向当时工作目录；归档文件位置及哈希以 `run.json` 为准。
完整工程不再逐次覆盖，也不会自动删除，需自行安排空间和备份。

## 重跑一批

`run.json` 的 `replay_command` 是命令参数数组。它使用归档源码和配置，
通过 `--workspace` 指定输出工作区。每次复现都会生成新的时间编号。

例如在已加载 Vivado 环境的终端执行：

```python
import json
import subprocess
from pathlib import Path

record = json.loads(Path("reports/history/2026.1/实际运行编号/run.json").read_text())
subprocess.run(record["replay_command"], check=True)
```

归档不含商业 Vivado 安装、IP Catalog 或许可证，需要保留相同工具环境。
相同源码、配置、策略版本和种子应生成相同输入和期望值。
XCI 可能含工具元数据，其哈希不保证跨版本相同。

## 续跑与中断

`--resume-from` 不是复现，而是跳过历史批次中完整通过的配置：

```bash
python3 scripts/run_all.py --config configs/bug_discovery.json \
  --resume-from reports/history/2026.1/实际运行编号/run.json --limit 3
```

只有 Vivado 版本、配置、源码和归档哈希核对一致，才允许跳过。可多次指定历史记录。
失败或未完成的配置从创建阶段重跑；工具或环境改变后应重新测试，不沿用跳过结果。

中断时保留已完成阶段；正在执行的日志可能还只在工作日志目录。
硬断电或 SIGKILL 不保证最后一步完成归档。没有待执行配置时不新建批次，
也不切换 `latest`。

## 数量核对

```text
generated_count = unique_count <= case_budget
checked_transaction_count = output_count
expected_output.txt 与 actual_output.txt 逐行一致
```

连续模式下各输入对通常各算一次。Multiplier 保持输入时仍每周期计算，
所以实际事务数可多于不同输入数；对应关系在 `schedule.json`。
Python 文件复核和 HDL 自检使用同一份期望值，不是两个独立参考模型。

无 Vivado 的 CI 只检查 Python 部分。真实 IP 仿真须在有相应安装和许可证的环境执行。

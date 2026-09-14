# 贡献指南

## 修改范围

公共流程按 `ip_type` 调用插件，不读取某个 IP 的端口或计算规则。
各 IP 的参数、参考模型、模板、Tcl 和测试放在各自目录。
生成策略只选择输入，不调用 Vivado，也不修改 testbench 的判定方法。

不要手动修改 Vivado 生成文件，不提交 `runs/`、`reports/` 中的产物。
新增 IP 的步骤见[插件开发](docs/plugin_development.md)。

## 本地检查

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 -m py_compile scripts/run_all.py
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/run_all.py
git diff --check
```

没有 Vivado 时仍可运行编译检查和单元测试，但要说明没有做真实仿真。
默认回归应有 19 条阶段记录；同时检查 `run.json` 是否完整结束，
不能只看已有行是否都为 PASS。详细要求见[验收清单](docs/framework_acceptance.md)。

需要检查安装入口时，在独立 Python 环境执行 `python3 -m pip install -e .`，
然后在仓库根目录运行 `vivado-ip-test --list-cases`。

## 文档和提交

文档用简短、平实的中文，写清操作和限制，避免重复说明。
命令、路径和协议名称保留原文。示例产物目录也要带日期和时间。

一个提交只处理一个明确的改动；提交说明写实际变化，不把计划当成已完成功能。

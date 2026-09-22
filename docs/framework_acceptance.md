# 框架检查清单

检查的是自动流程能否运行、报错和复现，不要求这次检查就找到真实 IP bug。

## 执行命令

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 -m py_compile scripts/run_all.py
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/run_all.py
VIVADO_INTEGRATION=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_failure_detection.py' -v
VIVADO_INTEGRATION=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_cycle_failure_detection.py' -v
VIVADO_INTEGRATION=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_masked_failure_detection.py' -v
VIVADO_INTEGRATION=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_multiply_adder_failure_detection.py' -v
VIVADO_INTEGRATION=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_complex_multiplier_failure_detection.py' -v
VIVADO_INTEGRATION=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_stream_failure_detection.py' -v
git diff --check
```

## 核对结果

| 项目 | 检查内容 |
| --- | --- |
| 默认回归 | 6 组配置、19 个阶段，与配置中的顺序一致，全部 PASS |
| 完成状态 | run.json 为 completed，全部阶段无异常时 outcome 为 NO_FAILURE_OBSERVED |
| 自检 | 输入、输出数量匹配，数值逐项一致；Divider 有效信号时序正确 |
| 报错能力 | 故障注入能捕获未知输出、提前有效、数据错误、回压不稳定、多余和丢失输出 |
| 流接口 | 只按握手比较，透明流收发笔数一致，位宽转换保持字节和包尾序列；回压保持及暂停计数可查看 |
| 有效位 | 原始输出完整保存；只忽略预先声明的不确定位，有效位错误仍失败 |
| 多处差异 | 首条证据保留，后续按阶段和字段归组；缺行、坏行、扫描中断和分组截断单独记录 |
| 目录 | 工程、日志、报告共用时间编号，各 IP 分开；重跑不改旧文件 |
| 归档 | 配置、源码和关键文件齐全，哈希一致，复现命令可执行 |
| 中断和超时 | 保留已完成记录，清理子进程，不把不完整批次判为通过 |
| 无 Vivado 开发 | Python 单元测试不需要商业工具 |

安装检查应在独立 Python 环境运行 `python3 -m pip install -e .`，
再不带 `PYTHONPATH` 运行测试和 `vivado-ip-test --list-cases`。
本地通过不等于远程 GitHub Actions 已通过。

综合后、布局布线后和板级测试不属于项目范围；自动输入缩减和根因去重尚未实现。
大矩阵无需在开发时全部运行。当前各 IP 的实际结果见
[Vivado 2026.1 全量运行记录](experiments/vivado_2026_full_regression.md)。

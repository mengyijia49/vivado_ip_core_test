# 2026-09-14 探索配置和目录整理记录

这是时间目录改造前的一次验收记录，保留当时的编号和路径。
环境为本机 Vivado 2025.2、XSim，全部使用 batch Tcl。

## 当时的结果

| 检查 | 结果 |
| --- | --- |
| 单元测试 | 104 项，102 通过，2 项需显式启用的集成测试跳过 |
| 默认回归 | 6 组配置、19 阶段通过，6 份输出哈希与整理前相同 |
| 探索验收 | 14 个实验、42 阶段通过，包含全部 10 组参数 |
| 不同输入对数量之和 | 916,991，未跨实验去重 |
| 实际比较次数 | 1,507,927 |
| 输入覆盖目标 | 14 个实验均命中全部声明目标 |
| XSim 故障注入 | 2 个测试方法、3 个场景均捕获预期错误 |
| 续跑 | 核对归档后跳过 14 个已完成实验 |
| JSON Schema | 两个公共入口和四个 IP 参数文件通过 |
| 旧文件迁移 | 204 个条目移动前后内容哈希相同 |

未在仓库根目录重新产生 .Xil、xvlog.pb、vivado.log 或 vivado.jou。

只仿真了选取的 14 个实验，没有跑完 90 个探索实验。
故障注入分别为 Divider 未知输出、Multiplier 未知输出和 Divider 提前有效；
这些是人为错误，不是 AMD IP bug。

## 文件位置

- 首次整理后回归：`reports/history/20260914T120808_a3fa386102f3/`。
- 探索验收：`reports/history/20260914T121258_3ec2e3cd9030/`，有 564 个带哈希文件。
- 故障注入日志：`runs/logs/framework/acceptance/failure_detection.log`。
- 单元测试日志：`runs/logs/framework/acceptance/unit_tests.log`。
- 最终回归日志：`runs/logs/framework/acceptance/final_regression.log`。
- 迁移清单：`reports/maintenance/20260914T120755/layout_migration.json`。

整理后诊断脚本的位置又有变化，因此探索续跑使用原归档源码核对，没有跳过源码校验。

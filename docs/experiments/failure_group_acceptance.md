# 多处差异汇总验收

2026-09-15，Vivado 2025.2。此次只改失败分析和输出布局记录，
没有增加 IP 类型，也没有修改输入生成、参考运算或 VHDL 模板。
目的是避免首条失败遮住后面的线索，不是按差异数量增加 bug 数。

## Python 检查

`py_compile` 通过。完整测试共 623 项，452 项通过、171 项条件跳过，耗时约 812 秒。
包含 5,084,282 组参数的完整配置校验，不代表这些配置均已运行 Vivado。
检查前后 278 个运行源码、214 个测试文件和 1325 个配置文件的哈希一致。
完整套件峰值内存约 6.53 GiB，不是低内存测试。
见[命令、日志和核对结果](../../reports/framework/failure_group_validation/2026-09-15_12-17-00_UTC+0800_100ce169/summary.json)。

## 真实回归

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --all --case intc_rise1_sw2 --case intc_mixed32 \
  --case acc_signed_control --case axis_reg_full32 --case dwidth_3_5 --case switch_cross3to3
python3 scripts/run_all.py
```

第一批编号为 `2026-09-15_12-17-07_UTC+0800_5daa8838`，六组配置完成 18 个阶段。
15 个阶段 PASS，累加器和两组 INTC 的自检保留原有失败。

| 配置 | 汇总结果 |
| --- | --- |
| intc_rise1_sw2 | 885 条数值差异，15 个观察组；首条仍为序号 17，硬件中断阶段的 IRQ 差异从 1012 开始 |
| intc_mixed32 | 1883 条数值差异，97 个观察组；32 路硬件中断阶段各自有 IRQ 差异记录 |
| acc_signed_control | 1 条数值差异，提前停止后缺少 533 行；没有把缺行当成 533 次独立数值错误 |
| 三组流接口 | 全部通过，布局分别对应按拍、字节和分路输出 |

所有失败文件均已读完，分组没有截断。两组 INTC 与前一批的输入、期望值、掩码和
实际输出完全一致，testbench 除运行路径外一致。完整失败文件已归档，报告摘要及哈希核对通过。
见[回归核对](../../reports/framework/failure_group_audit/2026-09-15_12-20-28_UTC+0800_97e125ba/summary.json)。

默认回归编号为 `2026-09-15_12-19-42_UTC+0800_03bd55a4`，六组、19 个阶段全部 PASS。
六组输入和实际输出与前一版一致，278 个运行源码及 516 个归档文件哈希核对通过。
见[默认回归核对](../../reports/framework/failure_group_default_audit/2026-09-15_12-24-41_UTC+0800_061b70c1/summary.json)。

## 历史文件与故障注入

- 12 组历史 INTC 输出的 19,267 条差异均保留，792 个历史文件未被改写。
  旧清单没有字段布局，按整体输出分组，不猜测端口。
  见[历史分析](../../reports/framework/failure_group_history/2026-09-15_12-17-38_UTC+0800_11b9426c/summary.json)。
- 从 10 类 IP 的历史失败中各取一例，首条证据与旧报告一致。
  其中包含后来已修复的模型和生成问题，不是当前 bug 清单。
  见[兼容性检查](../../reports/framework/failure_group_compatibility/2026-09-15_12-23-27_UTC+0800_9a90ac9c/summary.json)。
- 两组大预算历史输出共 262,038 行，分别保留 19,003 和 32,405 条差异。
  分析耗时约 1.33 秒和 0.93 秒，进程峰值内存约 180 MiB。这不是 Vivado 仿真耗时，
  也不是整个测试套件的内存占用。输入 JSON 仍整份载入内存。
  见[大输出检查](../../reports/framework/failure_group_large_output/2026-09-15_12-23-55_UTC+0800_b58c350b/summary.json)。
- 8 项真实 XSim 检查全部通过，包括三个正常对照以及未知输出、错值和漏输出。
  它们验证框架报错能力，不是厂商缺陷。
  见[故障注入命令和结果](../../reports/framework/failure_group_injection/2026-09-15_12-22-51_UTC+0800_df6eab62/summary.json)。

分组格式、上限及不完整扫描的含义见[报告格式](../report_format.md)。
自动输入缩减、根因去重、厂商确认仍未完成。

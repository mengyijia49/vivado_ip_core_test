# 报告格式

每批报告保存在 `reports/history/<run_id>/`。
`reports/latest` 指向最近启动的一批，`ip/<ip_type>/` 保存各 IP 的独立报告。
新批次只切换链接，不覆盖旧报告。

## 先确认是否跑完

`run.json` 记录运行状态和预期阶段：

| 字段和值 | 含义 |
| --- | --- |
| `state=running` | 已启动，尚未记录结束 |
| `state=completed` | 正常结束，仍需看 outcome |
| `state=interrupted/error` | 被中断或发生 Python 异常 |
| `outcome=NO_FAILURE_OBSERVED` | 预期阶段全部完成，未发现异常 |
| `outcome=FAILURES_OBSERVED` | 有失败阶段 |
| `outcome=INCOMPLETE` | 尚未完成全部检查 |

报告每阶段更新。只有已有行都为 PASS，不能说明缺少的阶段也通过了。

## CSV 和 JSON

`report.csv` 每阶段一行，前三列固定为 `case_id,stage,status`。
其余列包含 IP 类型、参数、策略、版本、种子、预算、覆盖目标、指标和文件路径。
参数和指标中含 JSON，应使用 CSV 解析器，不要按逗号切分。

`report.json` 是阶段记录数组，包含完整的 `verification` 设置，
包括边界、输入顺序和时序字段。脚本统计优先读取 JSON。

## 指标

| 字段 | 含义 |
| --- | --- |
| `directed_count` | 生成结果中属于定向集合的输入数 |
| `generated_count`、`unique_count` | 最终输入数和去重输入数，两者应相等 |
| `input_space_size`、`input_space_fraction` | 合法输入总数和本批不同输入所占比例 |
| `coverage_model` | 输入分类版本，当前 input_bins:1.0 |
| `target_coverage` | 各目标命中数、分类总数、比例和可列举的未命中项 |
| `covered_targets`、`missing_targets` | 全部命中或尚有遗漏的目标 |
| `checked_transaction_count` | 含保持周期重复计算的待检查事务数 |
| `input_cycles`、`gap_cycles` | 调度的输入周期和间隔/保持周期 |
| `max_observed_gap` | 实际最大间隔或保持长度 |
| `schedule_version` | 时序调度版本，当前 1.0 |
| `output_count` | 实际输出行数 |
| `actual_output_sha256` | 实际输出文件哈希 |
| `elapsed_seconds` | 阶段实际耗时，受机器负载影响 |
| `returncode`、`timed_out` | 外层 Vivado 返回码和是否超时 |
| `failure_evidence` | 自检失败时的差异记录，尚未确认根因 |

生成阶段记录输入和调度指标，仿真阶段记录输出指标。
失败时只要实际输出文件存在，也记录其行数和哈希。

每次 Vivado 调用另有 `.process.log` 和 `.invocation.json`，
分别保存标准输出/错误，以及命令、起止时间、返回码。
即使 Vivado 自身日志未生成，也可以用它们排查启动问题。

输入覆盖不足和数值错误是两回事。各字段的覆盖含义见[生成策略](test_generation_strategies.md)。

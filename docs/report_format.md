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
宽侧带的覆盖指标可能超过 Python 默认的 CSV 单字段读取限制，读取 JSON 不受这个限制。

Inline HDL 没有独立 XCI。缺少其 `.bd` 时报告 `BLOCK_DESIGN_NOT_FOUND`，
其他 IP 仍使用 `XCI_NOT_FOUND`。生成清单的产物键分别为 `block_design` 和 `xci`，
实际 `.bd` 及生成的行为 HDL 在创建成功后归档并计算哈希。

## 指标

| 字段 | 含义 |
| --- | --- |
| `directed_count` | 生成结果中属于定向集合的输入数 |
| `generated_count`、`unique_count` | 最终输入数和去重输入数，两者应相等 |
| `input_space_size`、`input_space_fraction` | 合法输入总数和本批不同输入所占比例 |
| `coverage_model` | 输入分类版本，当前 input_bins:1.0 |
| `target_coverage` | 各目标命中数、分类总数、比例和可列举的未命中项 |
| `covered_targets`、`missing_targets` | 全部命中或尚有遗漏的目标 |
| `checked_transaction_count` | 待检查事务数；逐周期后端不计完全没有有效输出位的周期 |
| `checked_output_samples` | 无输入常量的计划观察次数，不是输入事务数 |
| `input_cycles`、`gap_cycles` | 调度的输入周期和间隔/保持周期 |
| `max_observed_gap` | 实际最大间隔或保持长度 |
| `schedule_version` | 时序调度版本，当前 1.0 |
| `output_count` | 实际输出行数 |
| `output_branch_count`、`checked_output_transfers` | 按拍流后端的支路数和期望输出传输总数 |
| `input_lane_count`、`checked_input_transfers` | 按拍流后端的输入路数和期望输入握手总数 |
| `source_timing_pattern` | 单输入或多路独立输入的调度名称及版本 |
| `actual_output_sha256` | 实际输出文件哈希 |
| `elapsed_seconds` | 阶段实际耗时，受机器负载影响 |
| `returncode`、`timed_out` | 外层 Vivado 返回码和是否超时 |
| `failure_evidence` | 自检失败时的差异记录，尚未确认根因 |
| `failure_detail_file`、`failure_detail_sha256` | 相对该行 run_dir 的完整差异文件路径及哈希 |
| `defined_output_bits_by_port` | 各端口计划比较的有效位总数，不是状态覆盖率 |
| `fully_masked_cycles`、`masked_output_bits` | 所有输出均不确定的周期数，以及不比较的位总数 |
| `masked_reason_cycles` | 各端口出现某种不确定原因的周期数 |
| `reference_sequence_events` | Python 参考序列中的读写、冲突、回绕等事件数，不是 DUT 内部覆盖率 |
| `reference_contract` | 数值参考的假设及适用范围；CORDIC 明示精确数学舍入不等于厂商位精确模型 |

生成阶段记录输入和调度指标，仿真阶段记录输出指标。
常量的 `input_space_kind=no_external_inputs`、`comparison_kind=constant_observation`，
预算为一个无输入状态，`checked_transaction_count=0`。其实际观察次数仍看 `output_count`，
不能用唯一状态的 100% 输入比例证明所有参数、时间和内部行为都已覆盖。
失败时只要实际输出文件存在，也记录其行数和哈希。
复数乘法的 `valid_output_samples` 含 CE 暂停时重复观察的有效输出周期，
不能把它当作新输出事务数；这些计数位于参考序列指标中，不是实际 DUT 计数。
广播器一行输出汇集同一输入在所有支路的接收值，`output_count` 不是支路接收数之和。
各支路的实际握手数、回压和先于上游完成的次数见 `protocol_summary.txt`。
汇合器每行输入包含各路的一组值，每行输出是一次合成结果。
它的 `input_cycles` 使用每组各路最大间隔计算，不包含 DUT 回压造成的等待；
实际握手和暂停数仍看 `protocol_summary.txt`。
交换器每行是一笔收发，`input_groups` 是数值组数，乘输入路数得到总输入传输数。
输出按来源和输出端口分队列后合并，不代表真实到达顺序；周期顺序看事件日志。
`expected_transfers_by_source_and_output` 是计划计数，实际值看 `protocol_summary.txt`。
`offered_contention_cycles` 只统计当前有效输入对同一输出的竞争，不表示内部仲裁状态覆盖。
来源编号占用的位和定向路由不计入数值空间，范围由 `numeric_coverage_scope` 明示。
AXI-Lite 的 `command_count` 是展开后的操作数，包含定向访问、引脚变化和复位，
不等于策略选择的数值组数。`planned_actions`、`planned_register_accesses` 和
`planned_write_strobes` 是计划计数，实际握手数在 `protocol_summary.txt`。
`masked_reason_operations` 逐项记录不比较的原因；GPIO 寄存器只比较定义的有效字段。
`mismatches.txt` 保留所有数值差异，协议错误则立即结束仿真。
失败证据中的 `preceding_operations` 和 `preceding_reset_operation_index` 帮助定位历史操作，
不是自动缩减后的最小复现，也不是已经确认的原因。
CORDIC 的数学差异还需结合 `reference_contract` 和内部精度规定审查，
不能把 `SIMULATION_FAILED` 或 `UNTRIAGED` 直接统计成 IP bug。
Floating-Point 转换的同一字段还记录下溢判断规则及手册冲突。
平方根使用独立模型编号，另记录 `cycles_per_operation` 和末尾观察周期 `drain_cycles`。
两者用于运行配置和漏发、多发检查，不表示已经验证固定延迟或吞吐率性能。
Absolute 的 `dut_clock_present=false` 表示 DUT 没有时钟，流后端的周期指标是测试采样节拍。
浮点比较的 `case_budget` 是策略选取的 A/B 数值及用户字段组合数，不包含派生的操作码。
可编程模式对每组执行七种操作，再加定向前缀，因此实际输出数看 `checked_transaction_count`。
`checked_input_transfers` 是该数乘以输入路数；实际接收数分别记录在 `protocol_summary.txt`。
该文件的 `max_accepted_operand_skew` 表示各路累计接收数的最大差，不是内部 FIFO 深度。
`partial_input_cycles` 记录部分输入有效而另一些尚未有效的周期数，不是内部状态覆盖率。
比较器的 `input_cycles` 是各组最大计划间隔之和，不是独立并行输入的实际完成时间。

超过 13000 位的 `input_space_size` 和目标 `total_count` 用 `0x...` 字符串精确保存，
较小数量仍为 JSON 整数。Python 可用 `int(value, 16)` 读回大数量。
这避免关闭 Python 的十进制转换保护。若命中数非零但比例小到浮点数无法表示，
会附带 `input_space_fraction_underflow=true` 或目标内的 `fraction_underflow=true`，
不能把这样的 0.0 解读成从未命中。

逐周期后端的 `vectors.json`、`cycles.json` 也保留超宽数值：超过 13000 位时写成
`0x...` 字符串，其余仍是 JSON 整数。覆盖标签相应用 `Op1:0x...` 等形式。
生成清单标注 `numeric_value_encoding=integer_or_hex:1.0`。
读取某个值时，字符串用 `int(value, 16)` 还原，整数直接使用。
失败记录中的输入沿用同一格式；二进制输入、期望输出和实际输出文件不受影响。

每次 Vivado 调用另有 `.process.log` 和 `.invocation.json`，
分别保存标准输出/错误，以及命令、起止时间、返回码。
即使 Vivado 自身日志未生成，也可以用它们排查启动问题。

输入覆盖不足和数值错误是两回事。各字段的覆盖含义见[生成策略](test_generation_strategies.md)。

## 一次运行中的多处差异

自检失败后，Python 扫描已有的全部期望输出、实际输出和掩码。
`outputs/failure.json` 仍保留首条差异，另增加 `difference_summary`：

| 字段 | 含义 |
| --- | --- |
| `difference_rows` | 出现差异的行数，一行只计一次 |
| `difference_kind_counts` | 数值不符、缺行、额外输出、格式错误等各自的数量 |
| `artifact_issues` | 缺文件、读文件失败、无有效比较位等文件级问题数 |
| `all_rows_visited` | 是否读完已有文件；不表示仿真完整或测试通过 |
| `groups` | 按差异类型、输入阶段、输出字段及可用的流路由分组 |
| `rows_without_input_mapping`、`layout_issue_rows` | 无法确定输入位置或输出字段的差异行数 |
| `groups_truncated`、`omitted_group_memberships` | 是否超过分组上限，以及未保留的行与字段归组次数 |

每组记录数量、首末输出位置和最多三个位置示例，默认最多保留 256 组。
达到上限后仍扫描全部行，已保留组的计数继续更新。
一行可涉及多个字段，因此各组计数之和可能大于差异行数；省略计数也不是独立组数。
组内首条值只预览前 256 个字符，截断时记录完整位宽。
顶层首条证据及原始输出文件不截断。CSV/JSON 阶段报告只保存不含 `groups` 的摘要，
完整组列表通过 `failure_detail_file` 查阅，归档时一起保存并核对哈希。

新生成的 `manifest.json` 用 `output_layout` 明确二进制行从左到右的字段顺序。
这是比较文件的布局，不一定是 DUT 原始端口：位宽转换器是字节记录，交换器是分路记录。
旧清单没有布局或布局位宽不符时，使用 `packed_output` 并记录原因，不反推端口。
读文件中断会标记分析不完整；格式坏行仍报告并继续读后面的行。
输出按行读取，但输入上下文 JSON 仍会载入内存。

分组只是排查入口，不是根因去重或 bug 数量。
数值没有差异也不会覆盖协议失败、超时或编译失败的状态。
若 testbench 提前停止，尚未产生的后续输出无法恢复；缺失的输出另记为缺行。

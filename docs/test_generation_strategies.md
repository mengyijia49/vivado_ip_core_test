# 测试生成策略

插件定义哪些输入合法、结果怎么算；策略决定选哪些输入。
策略不调用 Vivado，也不修改仿真和判定逻辑。

## 当前三种策略

| 策略 | 做法 | 预算要求 |
| --- | --- | --- |
| `directed_random:1.0` | 先放入去重后的定向边界，再随机补足 | 不小于定向集合，不超过合法空间 |
| `exhaustive:1.0` | 按固定顺序遍历全部合法输入 | 能容纳整个空间 |
| `coverage_guided:1.0` | 从候选池中逐次选择能命中最多新分类的输入 | 生成到预算数量，大预算下开销较大 |

定向随机接近输入空间饱和时会改用顺序遍历，避免一直抽到重复值。
覆盖引导得分相同时保留候选顺序。相同源码、配置和种子应生成相同向量。

## 插件提供什么

`CaseSpace` 包含：

| 字段 | 含义 |
| --- | --- |
| `directed_cases` | 定向边界输入 |
| `random_case` | 用传入的随机数生成器选一个合法输入 |
| `exhaustive_cases` | 遍历全部合法输入 |
| `total_case_count` | 合法输入总数 |
| `coverage_features` | 一个输入命中了哪些分类 |
| `target_bins` | 每个覆盖目标包含哪些分类 |

策略实现 `VectorGenerationStrategy.generate(space, profile)`，
返回 `GenerationResult`。通过 `StrategyRegistry` 注册名称和版本；
配置版本必须与实现一致。

## 覆盖率是什么意思

所有策略都由 `StrategyRegistry` 按 `input_bins:1.0` 统计输入分类。
目标的全部分类都命中才记入 `covered_targets`，否则放入 `missing_targets`。

| 目标 | 统计内容 |
| --- | --- |
| `boundary_values` | 各操作数最小值和最大值，排除非法零除数 |
| `sign_combinations` | 正负组合，零按非负处理 |
| `nonzero_divisor` | 除数的正负类别 |
| `full_precision` | 乘积高于最大输入位宽的部分为零或非零 |
| `operand_magnitude` | 操作数绝对值的有效位数，零单独统计 |
| `systematic_values` | 各操作数的系统边界值是否出现 |
| `division_relations` | 整除、余数为一、余数接近除数，以及被除数绝对值小于或不小于除数 |
| `complete_input_space` | 不同输入数量占合法空间的比例 |

这些是输入覆盖率，不是 HDL 代码覆盖率，也不是 IP 内部状态覆盖率。
`systematic_values` 不表示边界值的所有两两组合都测过。
数值是否正确仍由自检决定，覆盖不足不自动导致仿真失败。

## 接入研究算法

实现相同策略接口，注册独立名称和版本，然后在配置中选择它。
算法只使用 `CaseSpace` 和测试设置，沿用现有参考模型与 testbench。

比较算法时固定 IP 参数、预算、种子集合和覆盖分类版本。
报告字段见[报告格式](report_format.md)；当前尚未接入研究算法。

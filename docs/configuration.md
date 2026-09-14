# 配置格式

## 文件怎么分

配置版本为 2。公共入口只引用各 IP 的文件：

```json
{
  "schema_version": 2,
  "includes": [
    "ip/divider/regression.json",
    "ip/multiplier/regression.json"
  ]
}
```

路径相对于引用它的配置文件解析。一个文件只能使用 `cases` 或 `includes`，
不能同时使用；一个 `cases` 文件只放一种 IP。
加载器会拒绝循环引用、重复 `case_id` 和不合法的阶段顺序。

公共格式在 `configs/schemas/ip_matrix.schema.json`，各 IP 参数格式在
`configs/schemas/ip/<ip_type>/`。运行时由 Python 加载器和插件校验，无额外依赖。
参数示例见 [Divider](ip/divider/configuration.md) 和 [Multiplier](ip/multiplier/configuration.md)。

## 一组配置的字段

| 字段 | 含义 |
| --- | --- |
| `case_id` | 唯一名称，不用于选择插件 |
| `ip_type` | 插件名称，也是分类目录名 |
| `vendor`、`ip_name` | Vivado Catalog 中的厂商和 IP 名称 |
| `parameters` | 当前 IP 的参数 |
| `stages` | 执行顺序，必须以 create_ip 开始，自检前先生成 testbench |
| `verification` | 输入生成和时序设置，见下表 |

## 测试设置

| 字段 | 要求或默认值 | 含义 |
| --- | --- | --- |
| `strategy` | 必填 | directed_random、coverage_guided 或 exhaustive |
| `strategy_version` | 必填，当前 1.0 | 策略版本 |
| `random_seed` | 必填，非负整数 | 随机种子 |
| `case_budget` | 必填，正整数 | 不同输入对的预算，不含保持周期的重复计算 |
| `coverage_targets` | 必填，非空、不重复 | 插件支持的输入覆盖目标 |
| `boundary_mode` | basic | basic 为基础边界；systematic 为系统边界 |
| `input_order` | generated | generated 保留生成顺序；shuffled 打乱顺序 |
| `timing_mode` | continuous | continuous、random_gaps 或 bursts |
| `max_gap_cycles` | 8，范围 1 至 10000 | 最大间隔；无使能 IP 中指输入保持周期 |
| `burst_length` | 16，范围 1 至 10000 | 每段连续事务数量 |

数值、顺序和间隔使用独立随机流。只改时序不会改变选中的数值集合。
定向随机预算不能小于定向集合或大于合法空间；穷举预算须容纳整个合法空间。
覆盖引导逐次搜索候选，预算大时较慢，默认探索配置没有使用它。

## 多种子和时序组合

`configs/bug_discovery.json` 在公共入口增加以下设置：

```json
{
  "schema_version": 2,
  "includes": ["ip/divider/discovery.json", "ip/multiplier/discovery.json"],
  "exploration": {
    "seeds": [20260914, 20260915, 20260916],
    "timing_modes": ["continuous", "random_gaps", "bursts"]
  }
}
```

只有本次加载的顶层允许 `exploration`。展开后的名称为
`<case_id>__seed<seed>__<timing_mode>`，`--case` 要使用这个完整名称。
`--limit` 限制本次实验数，不是每个实验的输入数量。

展开矩阵不能再用 `--seed` 覆盖，请修改 `exploration.seeds`。
单独加载某个 IP 的 `discovery.json` 时，可以使用 `--seed`。

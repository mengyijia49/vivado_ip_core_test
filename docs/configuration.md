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

路径相对于引用它的配置文件解析。一个文件只能选择 `cases`、`includes` 或 `sweeps`。
`cases` 和 `sweeps` 文件只放一种 IP；公共入口只用 `includes`。
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
| `case_budget` | 必填，正整数 | 不同输入组合的预算，不含定向时序前缀、间隔和刷新周期 |
| `coverage_targets` | 必填，非空、不重复 | 插件支持的输入覆盖目标 |
| `boundary_mode` | basic | basic 为基础边界；systematic 为系统边界 |
| `input_order` | generated | generated 保留生成顺序；shuffled 打乱顺序 |
| `timing_mode` | continuous | continuous、random_gaps 或 bursts |
| `max_gap_cycles` | 8，范围 1 至 10000 | 最大间隔；无使能 IP 中指输入保持周期 |
| `burst_length` | 16，范围 1 至 10000 | 每段连续事务数量 |

数值、顺序和间隔使用独立随机流。只改时序不会改变选中的数值集合。
定向随机预算不能小于定向集合或大于合法空间；穷举预算须容纳整个合法空间。
覆盖引导逐次搜索候选，预算大时较慢，默认探索配置没有使用它。

## 参数扫描

各 IP 的 `extended.json` 使用 `sweeps`，避免手写成千上万条重复配置。
每组扫描包含 `case_prefix`、`template` 和 `axes`：

- `template` 与普通 case 相同，但不写 `case_id`。
- `axes` 写需要变化的参数及取值，加载器生成这些取值的笛卡尔积。
- 例如 `axes: {"width": [8, 16], "depth": [16, 32]}` 生成四组参数。
- 名称包含前缀、参数名和取值，重排取值不会重命名已有配置。
- 相关参数不能随意交叉，例如加法器输出位宽必须符合输入位宽；此时拆成多组扫描。

数组参数或很长的常量可写成命名选项，例如：

```json
"axes": {
  "input_widths": [
    {"label": "mixed", "value": [1, 7, 33]},
    {"label": "uniform", "value": [8, 8]}
  ]
}
```

此时 `label` 进入 case_id，`value` 进入实际参数。命名选项支持标量和非空标量数组，
不支持嵌套对象。一个轴内的名称和值都不能重复；不要改用同一名称指代另一套参数。
完整值仍会写入报告和复现配置，修改原始配置不会改写历史运行记录。

每个文件最多展开 20000 组，展开后的参数仍经过插件校验。
`configs/extended_regression.json` 是常用回归；`configs/extended_discovery.json`
是大参数矩阵。后者每组只用一套输入设置，没有 `exploration`。
可用 `--ip-type`、`--case`、`--limit` 选择本次运行内容。
配置现在逐项读取，`--limit` 只保留本次要执行的配置，不把全部候选留在内存。
整份入口仍须扫描完：格式、全局重名和所选 IP/用例的参数错误都在 Vivado 启动前报告，
不会因为已选够数量就忽略后面的错误。续跑跳过已完成项之后，再计算本次数量。
大矩阵仍建议用 `--config` 指向某个 IP 的叶文件，减少扫描时间。
不设置 `--limit` 时，所有待执行配置仍会保留；它不是无限内存的全量运行方式。

普通单元测试会完整校验 323 组常用回归，并快速核对大矩阵入口、36 类 IP 和静态展开数量。
逐项校验大矩阵的 9472890 组参数耗时长、占用内存高，不放在每次 GitHub Actions 中运行。
需要完整审计时使用：

```bash
VIVADO_FULL_MATRIX_AUDIT=1 PYTHONPATH=src python3 -m unittest \
  unit.test_parameter_sweeps.SweepTests.test_all_shipped_matrices_validate_without_vivado -v
```

超过 8192 个名称后，去重使用临时 SQLite 索引，比较完整名称，不使用概率过滤器。
临时索引位于系统临时目录，目录名含时间，正常结束、校验失败和可处理的中断都会删除。
它不作为运行证据，也不会在下次加载时复用；磁盘空间不足按配置错误退出。
源码、参数和实际实验报告仍按原来的时间编号归档。
实测内存、兼容性和分批续跑结果见[大矩阵读取检查](experiments/config_streaming_acceptance.md)。

时序 IP 的“完整输入空间”只指单周期端口组合，不等于穷举全部状态和输入序列。
报告另记实际比较周期数，并将序列覆盖标为尚未测量。
AXI-Stream 的输入预算只计算数据及已启用的 ID、DEST、USER 组合；
TLAST 由包长安排，KEEP、STRB 当前固定为全 1，不把它们算成已穷举的变量。
源端间隔和接收端回压分别生成，具体规则见 [流接口自检](protocols/axis_stream.md)。
存储器和原生 FIFO 的未定义结果按[有效位规则](protocols/defined_output_bits.md)处理，
不把无效输出算作数值错误，也不靠观察实际输出来决定是否忽略。

## 多种子和时序组合

需要比较种子或时序时才使用这个功能。旧的 `configs/bug_discovery.json` 保留如下设置：

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

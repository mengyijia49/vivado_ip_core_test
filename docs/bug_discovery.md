# 缺陷探索配置

默认 `configs/ip_matrix.json` 用于快速检查流程：6 组参数、238 个输入对。
`configs/bug_discovery.json` 用于较大规模探索，分别引用 Divider 和 Multiplier 的配置。

## 测试规模

10 组参数乘以 3 个种子、3 种时序，共 90 个实验、270 个阶段。
其中 180 个阶段调用 Vivado，90 个阶段由 Python 生成 testbench。

每个实验预算为 65,536 个不同输入对。4 组小位宽参数使用穷举，
其余用系统边界加随机输入。各实验输入数合计 5,893,623，
这是逐实验相加，不是跨实验去重数量。
相同参数和种子在不同时序下使用相同输入集合；穷举换种子只改变输入顺序。

## 怎么运行

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --config configs/bug_discovery.json --list-cases
python3 scripts/run_all.py --config configs/bug_discovery.json --limit 3
```

去掉 `--limit` 才会跑完整矩阵。先小批确认耗时和磁盘占用：
向量生成占用内存，每批还会保留完整工程、日志和输入输出，不自动清理旧文件。

续跑时核对旧批次后跳过已完成配置：

```bash
python3 scripts/run_all.py --config configs/bug_discovery.json \
  --resume-from reports/history/实际运行编号/run.json --limit 3
```

也可以只测一种 IP：

```bash
python3 scripts/run_all.py --config configs/ip/divider/discovery.json \
  --case hunt_div_s16_s8 --seed 123
```

续跑条件和重跑区别见[复现方法](reproducibility.md)。

## 边界和时序

系统边界包括最小/最大值、零、一、二的幂及相邻值、单比特、单零位、
交替位型和符号边界，并组合两个操作数。
Divider 另选取 `q*d+r` 附近的输入，覆盖整除和不同余数关系。
候选值先过滤非法情况，再去重并补随机输入。

| 模式 | Divider | Multiplier |
| --- | --- | --- |
| continuous | 两路 tvalid 同时有效，每周期送一对输入 | 每周期更新输入 |
| random_gaps | 两路 tvalid 同时无效 0 至 max_gap_cycles 周期 | 保持上一对输入相同数量的周期 |
| bursts | 每 burst_length 个事务后插入固定间隔 | 每段事务后保持上一对输入 |

Divider 没有 tready，不测试输出反压；另按 XCI 时延检查输出 tvalid。
NonBlocking 接收规则见 [AMD PG151](https://docs.amd.com/v/u/en-US/pg151-div-gen)。

Multiplier 没有 CE，保持输入时仍然计算，每个保持周期都要比较输出。
相关时钟和使能规则见 [AMD PG108](https://docs.amd.com/api/khub/documents/idOj3Pp9ocZdMoFz3IpkjQ/content)。

输入顺序可按种子打乱，间隔和流水线排空时间计入超时预算。
`unique_count` 统计不同输入，`checked_transaction_count` 统计实际待检查事务，
`input_cycles` 统计仿真输入周期，不是程序运行秒数。

## 结果和限制

每批保存在带日期、时分秒的独立目录，路径见[目录说明](directory_structure.md)。
失败时看阶段日志和 `outputs/failure.json`，按[异常排查](bug_hunting.md)复现。

当前不测试除零、商溢出、复位、反压、使能、Divider 分数模式，
以及 Multiplier 截位、舍入和常量乘法。
系统边界覆盖率也不表示测遍 IP 内部状态。增加输入量有助于扩大范围，
但不能保证找到 bug；还需要扩展参数、接口模式和 IP 种类。

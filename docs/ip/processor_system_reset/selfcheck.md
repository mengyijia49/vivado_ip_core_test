# Processor System Reset 自检

`processor_system_reset` 对应 `proc_sys_reset:5.0`，用于根据外部复位、辅助复位、
调试复位和时钟锁定状态，产生处理器、总线和外设复位。

```bash
python3 scripts/run_all.py --ip-type processor_system_reset
python3 scripts/run_all.py --config configs/ip/processor_system_reset/extended.json --list-cases
```

## 检查方法

Python 模型分别记录外部和辅助复位连续有效的周期数。短于配置窗口的脉冲不能触发复位；
达到窗口后，所有复位输出应进入有效状态。`dcm_locked` 变低也会触发全部复位。

释放时先检查 `bus_struct_reset` 和 `interconnect_aresetn`，16 个周期后检查两类外设复位，
再过 16 个周期检查 `mb_reset`。输出配置为多份时，每一位都必须一致。
外部输入经过同步器，手册允许一至两个周期的不确定延迟，因此只屏蔽各状态切换附近的周期，
稳定区间仍逐位比较。规则来自 [PG164](https://docs.amd.com/v/u/en-US/pg164-proc-sys-reset)。

## 配置范围

常用配置有 4 组，覆盖高低有效、1/3/4/5/16 周期过滤窗口，以及最少和最多输出副本。
大矩阵有 117 组：36 组检查过滤窗口和输入极性，81 组检查四类输出数量。
没有把两部分做笛卡尔积，因为输出副本数不改变输入过滤行为。每组还包含上电释放、
短脉冲、合法外部复位、辅助复位、调试复位和锁定丢失。

当前只做行为仿真。异步输入在真实硬件中的亚稳态不能由数字仿真重现；测试检查的是文档规定的
过滤和顺序，不把同步器允许的边界差异算作 IP 问题。大矩阵只完成参数校验，不会默认全部运行。

2026-09-22 使用 Vivado 2026.1 运行四组常用配置，12 个阶段均通过。
运行编号见[全量报告](../../experiments/vivado_2026_full_regression.md)。

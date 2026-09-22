# Clocking Wizard 自检

`clocking_wizard` 对应 `clk_wiz:6.0`，用于根据输入时钟生成指定频率的输出时钟。

```bash
python3 scripts/run_all.py --ip-type clocking_wizard
python3 scripts/run_all.py --config configs/ip/clocking_wizard/extended.json --list-cases
```

## 检查方法

Python 根据输入和输出频率计算理想周期及高电平宽度。testbench 等待 `locked` 变高，
连续测量 16 个输出周期和 16 个高电平宽度。随后拉起复位，确认 `locked` 变低；
释放复位后再次等待锁定，并重复测量。允许 5 ps 的数字仿真误差。

检查依据是 [PG065 输出时钟](https://docs.amd.com/r/en-US/pg065-clk-wiz/Configuring-Output-Clocks)、
[复位说明](https://docs.amd.com/r/en-US/pg065-clk-wiz/Resets)和
[端口说明](https://docs.amd.com/r/en-US/pg065-clk-wiz/Port-Descriptions)。

## 配置范围

常用配置有 4 组，覆盖 MMCM、PLL、50/100/200 MHz 输入、50/125/200 MHz 输出，
以及高有效和低有效复位。大矩阵有 48 组：36 组常用整倍数关系和 12 组 MMCM 的
25/125 MHz 边界组合。大矩阵只完成参数校验，不会默认全部运行。

2026-09-22 使用 Vivado 2026.1 运行四组常用配置，12 个阶段均通过。
运行编号见[全量报告](../../experiments/vivado_2026_full_regression.md)。

当前只做行为仿真。数字模型不能检查模拟抖动、相位噪声或真实器件上的锁定时间，
也没有覆盖多输出、相位偏移、动态重配置和输入时钟停止。

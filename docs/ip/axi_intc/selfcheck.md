# AXI INTC 自检

使用 `axi_intc:4.1` 的普通中断模式。Python 独立计算寄存器状态和 IRQ，
公共 AXI-Lite testbench 完成读写、输入驱动和结果比较，不使用官方 HDL 计算期望值。
依据为 [PG099 v4.1](https://docs.amd.com/v/u/en-US/pg099-axi-intc)。

## 运行

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type axi_intc
python3 scripts/run_all.py --ip-type axi_intc --case intc_mixed4_lowirq
python3 scripts/run_all.py --config configs/ip/axi_intc/extended.json --limit 3
```

前两条选择常用配置，第三条只取扩展矩阵前三组，按需选一条。
常用配置 12 组，扩展矩阵 8960 组；后者不是已经运行或通过的数量。
配置按单路、混合 4/8/16/32 路和 31 路上升沿分文件，位于 `configs/ip/axi_intc/extended/`。

## 参数

| 参数 | 含义 |
| --- | --- |
| `input_modes` | 1 至 32 个触发方式，数组第 0 项对应 intr(0)；可用 rising、falling、high、low |
| `software_interrupts` | 软件中断数量；与硬件输入路数之和不能超过 32 |
| `async_mask` | 对应硬件输入的同步器使能位，不允许超出输入路数 |
| `synchronizer_stages` | 0 至 7；未启用同步器时固定为 2，避免重复参数组合 |
| `irq_active_high` | 电平 IRQ 的有效极性 |
| `has_ipr/has_sie/has_cie/has_ivr/has_ilr` | 分别选择五个可选寄存器 |

扩展矩阵包含直接输入、全路同步的 0/2/7 级边界、交替输入使用 3 级同步器，
以及五个寄存器开关和 IRQ 极性的组合。其他合法同步级数可以自行配置。
创建后核对 XCI 中的实际参数、32 位数据和 9 位地址接口、intr 向量及 irq 标量。

## 检查内容

- ISR 写零保持、不同位累积置位、IAR 按位清除，以及 HIE 前后可写范围。
- 四种触发方式、输入恢复后仍保留状态、电平持续有效时重新置位、边沿确认后不重复触发。
- IER 屏蔽与重新开启、SIE/CIE 原子修改、空闲及挂起状态下的 ME 开关。
- 多路同时挂起时的优先级、ILR 阈值、复位清除状态和 HIE 写一次限制。
- AXI-Lite 响应、未知位、输出保持、读写超时，以及输入与输出文件复核。

每组定向测试有复位边界；随机部分每 16 个数值样本复位一次。
一个数值样本会展开为多次总线操作，报告中的操作数不等于独立 testcase 数量。
`vectors/vectors.json` 记录阶段名和原始样本索引，可以对照 `outputs/mismatches.txt` 排查。
普通数值差异不会立即停止仿真，后续操作和正向对照仍会留下记录。

## 当前限制

每次操作后等待 64 个时钟，输入在此期间保持稳定；这不是精确延迟或亚周期 CDC 检查。
支持总线响应回压，但尚未加入 AW/W 起始时间错开、未完成事务时复位。
只发完整 32 位写入，不读取写专用或未启用寄存器。
ILR 只严格比较 0 至中断总数的阈值和全一值；其他高位编码保留为独立观察。
启用 HIE 前的外部输入活动、带未清状态切换 HIE 尚未纳入参考模型。
Fast、级联、脉冲 IRQ 和独立处理器时钟尚未接入，不运行综合或网表仿真。

已保留 [ISR 写入异常](isr_write_issue.md)和[清除 ME 后 IRQ 仍有效](master_enable_issue.md)。
参考模型仍按手册比较，相关配置会报告失败；不能把测试命令返回非零直接当成环境故障。
真实结果见[2026.1 全量运行记录](../../experiments/vivado_2026_full_regression.md)。

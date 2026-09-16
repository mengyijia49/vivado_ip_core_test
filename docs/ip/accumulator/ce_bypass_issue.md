# CE 与 BYPASS 的待确认差异

## 现象

Vivado 2025.2，`c_accum:12.0` revision 21，Fabric，一级延迟，
8 位有符号输入、16 位输出，CE、SCLR、BYPASS 和动态 ADD 均启用。

时钟上升沿前设置输入，沿后 1 ns 采样；SCLR=0，ADD=1。

| 周期（从 0 开始） | B | CE | BYPASS | 当前模型 Q | 实测 Q |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 1 | 1 | 1 | 1 | 1 |
| 1 | 0 | 0 | 1 | 1 | 0 |

模型按 CE=0 时保持状态计算。实测在 BYPASS=1 时仍加载了 B。
[PG119 第 9 页](https://docs.amd.com/v/u/en-US/pg119-c-accum)说明 CE 关闭会暂停核心，
但 BYPASS 的说明没有明确它与 CE 的优先级。当前不能排除规范解释问题。
这是待确认的控制语义差异，不是已确认的硬件 bug，也没有计入 bug 数量。

## 复现和证据

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --all --case acc_signed_control
```

该配置预期会报告 `SIMULATION_FAILED`，不应改期望值或跳过比较来获得 PASS。
首次完整序列在周期 37 触发；缩短后的序列在周期 1 触发。

- 首次运行：`2026-09-14_21-52-45_UTC+0800_49f75f89`。
- 两周期复现：`2026-09-14_22-02-51_UTC+0800_04f9f225`。
- 报告：`reports/history/<run_id>/report.csv`。
- 证据：`runs/history/<run_id>/cases/accumulator/acc_signed_control/`。
- 日志：`runs/logs/history/<run_id>/accumulator/acc_signed_control/sim_selfcheck/`。
- 可提交的小证据包：[evidence/accumulator/ce_bypass](../../../evidence/accumulator/ce_bypass/README.md)。

归档中有 XCI、源码、testbench、完整输入、期望值、实际输出及 `failure.json`。
下一步应核对厂商对 BYPASS/CE 优先级的说明，再用另一版本 Vivado 的行为模型对照。
不加入综合后仿真；这个阶段不属于本项目的测试范围。
在结论明确前保持原始证据和模型假设，不把“行为符合另一种优先级”当成修复。

# 加减法器自检

配置位于 `configs/ip/adder_subtractor/`，IP 为 `c_addsub:12.0`。

- `a_width`、`b_width`、`output_width`：1 至 256 位；输出不得小于较宽输入，最多多一位。
- `a_type`、`b_type`：各自选择 Signed 或 Unsigned。
- `operation`：Add、Subtract、Add_Subtract；动态模式下 ADD=1 为加，ADD=0 为减。
- `latency`：0 或 1；0 是组合逻辑，不能启用 CE 和 SCLR。
- `clock_enable`、`sync_clear`、`ce_overrides_reset`：选择 CE、SCLR 及两者优先级。

模型先按各自符号解释 A、B，再加减，结果按输出位宽截断。
寄存模式在上升沿后比较 S，CE 暂停和同步清零也要检查。
系统边界会在 CE 有效且 SCLR 无效时驱动，不只检查复位状态下的端口变化。

当前固定 Fabric，不包含 DSP48、进位端口、常数 B、旁路和多级流水线。
端口、控制含义和延迟依据 [PG120](https://docs.amd.com/v/u/en-US/pg120-c-addsub)，
每次生成后再核对 XCI。实际结果见[2026.1 全量运行记录](../../experiments/vivado_2026_full_regression.md)。

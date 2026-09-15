# 累加器自检

配置位于 `configs/ip/accumulator/`，IP 为 `c_accum:12.0`。

- `input_width`、`output_width`：1 至 256 位，输出不得小于输入。
- `input_type`：Signed 或 Unsigned。
- `operation`：Add、Subtract、Add_Subtract。
- `clock_enable`、`sync_clear`、`ce_overrides_reset`：CE、SCLR 及优先级。
- `bypass`：添加 BYPASS，加载输入 B。

当前固定 Fabric、一级延迟、Scale=0，无进位输入。
模型保存累加状态，逐周期计算加减和溢出；定向序列包含加载、连续运算及控制冲突。
检查的是完整输入顺序，不把每个周期当成互不相关的算术题。

接口依据 [PG119](https://docs.amd.com/v/u/en-US/pg119-c-accum)。
CE 和 BYPASS 同时出现时存在 [待确认差异](ce_bypass_issue.md)，相关配置仍保留严格比较。
不能把该项失败或不同宽度下的重复触发，直接计为多个 IP bug。

# 计数器自检

配置位于 `configs/ip/counter/`，IP 为 `c_counter_binary:12.0`。

- `width`：1 至 256 位。
- `increment`：正整数，必须小于 `2**width`。
- `direction`：UP、DOWN、UPDOWN；动态模式下 UP=1 加，UP=0 减。
- `clock_enable`、`sync_clear`、`ce_overrides_reset`：CE、SCLR 及优先级。

当前固定 Fabric、一级输出寄存器、零反馈延迟，自由计数并启用高有效 LOAD。
LOAD=1 时从 L 加载，否则按步长计数；结果按位宽回绕。模型保存历史状态。
定向序列从零、最大值、中间值和步长附近加载，再连续计数，检查上下溢出。

不包含限制终值、阈值输出、同步置位和 DSP48 模式。
接口依据 [PG121](https://docs.amd.com/v/u/en-US/pg121-c-counter-binary)，
每次生成后核对 XCI 的位宽、步长和控制配置。

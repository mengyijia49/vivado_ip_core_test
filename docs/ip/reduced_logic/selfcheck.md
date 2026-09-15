# 归约逻辑自检

配置位于 `configs/ip/reduced_logic/`，IP 为 `util_reduced_logic:2.0`。
`width` 为 1 至 256；`operation` 为 and、or 或 xor。

Op1 是向量，Res 是单比特标量。没有时钟和握手信号。
模型分别检查是否全为 1、是否存在 1，以及 1 的个数是否为奇数。
检查包含全零、全一、单比特、交替位和位宽边界。

参数和端口来自本机 Vivado 的 `util_reduced_logic_v2_0/component.xml`，
运行时再核对 XCI。共享 testbench 会拒绝 X、U 等未知值，并先保存错误输出再停止。

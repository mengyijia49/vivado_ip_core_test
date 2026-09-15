# 按位逻辑自检

配置位于 `configs/ip/vector_logic/`，IP 为 `util_vector_logic:2.0`。
`width` 为 1 至 256；`operation` 为 and、or、xor 或 not。

二元运算使用 Op1、Op2 和 Res；not 只使用 Op1 和 Res。
没有时钟和握手信号，输入稳定后逐位比较结果。取反后按 width 截断。
宽度 1 仍是单元素向量，不能当成标量端口。

参数和端口来自本机 Vivado 的 `util_vector_logic_v2_0/component.xml`，
运行时再核对生成的 XCI。小位宽配置可穷举全部输入，大位宽使用系统边界和随机输入。

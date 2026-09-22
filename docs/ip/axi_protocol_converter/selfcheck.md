# AXI Protocol Converter 自检

本模块测试 `axi_protocol_converter:2.1` 把 AXI4 转成 AXI4-Lite 的行为。转换模式设为 2，
因此 AXI4 burst 会拆成多次 AXI4-Lite 单拍访问。

testbench 检查 FIXED、INCR 和 WRAP burst 的地址，窄传输、写数据、字节使能、保护属性、
读数据、ID 恢复、RLAST 和错误响应。下游会暂停 READY，上游也会暂时拒收响应，用来检查
VALID 和负载是否保持稳定。Python 参考模型独立列出每次 AXI-Lite 访问和上游应收到的响应。

当前只接入 AXI4 到 AXI4-Lite。AXI3、AXI4-Lite 到 AXI4、未保护模式和读写单向模式尚未
测试。该转换方向在本机 Catalog 中只允许 32 或 64 位数据。通过结果不能代替其他方向。

2026.1 全量运行中的 5 组配置、15 个阶段全部通过，
见[运行记录](../../experiments/vivado_2026_full_regression.md)。

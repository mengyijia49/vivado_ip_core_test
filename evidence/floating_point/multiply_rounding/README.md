# Floating-Point 乘法舍入证据

现象：双精度 Low_Latency 乘法在固定输入下输出约为 0.5，期望舍入结果为 1.0。Speed_Optimized 对照正常，厂商 C 数值模型对照正常。

完整证据包包含首次运行、独立复现、正常实现对照、C 模型对照、testbench、日志和 XCI 参数摘要。

本项仍需在其它版本和官方记录中继续核对。

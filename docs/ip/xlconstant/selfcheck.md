# 常量工具自检

对象是旧版 `xlconstant:1.1`，不是 Inline HDL 的 `ilconstant`。
Vivado 2025.2 已提示迁移；新版替代项还不能沿用旧版测试结果。

参数为 `width` 和字符串 `value`，输出只有 `dout`，没有输入、时钟、复位或握手。
位宽为 1 至 4096。常量必须放得进所选位宽，不能把越界参数当作正常截断测试。

按 [PB040 的常量写法](https://docs.amd.com/v/u/en-US/pb040-xilinx-com-ip-xlconstant)，
支持十进制、`b101` 二进制、`077` 八进制、`0xFF` 或 `0XFF` 十六进制。
这里的二进制前缀是 `b`，不是 `0b`。Python 独立解析原始参数，
再核对 XCI 中的实际常量和端口宽度，不把生成 HDL 当作参考答案。

```bash
python3 scripts/run_all.py --ip-type xlconstant
python3 scripts/run_all.py --config configs/ip/xlconstant/extended.json --list-cases
```

常用回归 8 组，大矩阵 17161 组。所有位宽都包含 0、1、最高位为 1 和全 1，
另有常见字长边界附近的值；同一位宽、同一数值不会仅因换写法而重复加入矩阵。

每组配置没有可变输入，只观察 64 次输出，采样时间为 206 至 836 ns。
报告的 `checked_output_samples` 为 64，`checked_transaction_count` 为 0。
唯一的无输入状态不代表“功能覆盖完整”，64 次观察也不等于 64 个不同 testcase。
它只能检查这段观察时间内的值、未知位和稳定性。
框架故障检查另包含 300 ns 后改变输出的例子，见[连接工具验收](../../experiments/utility_acceptance.md)。

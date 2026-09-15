# 复数乘法 IP 自检

`complex_multiplier` 对应 `cmpy:6.0`。只运行整数模式的行为仿真。

```bash
python3 scripts/run_all.py --ip-type complex_multiplier
python3 scripts/run_all.py --config configs/ip/complex_multiplier/extended.json --list-cases
```

## 检查方法

Python 按有符号整数计算：实部为 `ar*br-ai*bi`，虚部为 `ar*bi+ai*br`。
完整分量宽度是 A 宽度加 B 宽度再加一；缩短输出时丢弃低位，不是高位。
依据：[输出范围](https://docs.amd.com/r/en-US/pg104-cmpy/Output-Product-Range)。

截断直接取算术右移后的结果。Random_Rounding 由 CTRL 输入最低位决定临界点方向，
不是由 Python 临时随机决定。先加 `2^(丢弃位数-1)-1+ROUND_CY`，再截断，
正负数都使用同一规则。定向测试包含恰好半个量化单位及其两侧。
依据：[舍入说明](https://docs.amd.com/r/en-US/pg104-cmpy/Rounding)。

实部位于 TDATA 低位，两个分量各自按字节对齐。输入填充位会故意写入零或一，
检查它们没有影响数值；输出填充位应为符号扩展，也参与比较。
TUSER 按 A、B、CTRL 从低到高拼接，没有字节填充；TLAST 按配置直通、与或处理。
依据：[数据打包](https://docs.amd.com/r/en-US/pg104-cmpy/TDATA-Packing)、
[TUSER](https://docs.amd.com/r/en-US/pg104-cmpy/TUSER-Options)、
[TLAST](https://docs.amd.com/r/en-US/pg104-cmpy/TLAST-Options)。

当前使用 NonBlocking：没有 TREADY，所有已启用输入通道的 TVALID 必须同时为一，
结果才有效。逐周期比较输出 TVALID；有效时严格检查数据和侧带，无效时不比较载荷。
时钟使能为零时检查流水线保持。自动延迟从 XCI 读取并归档，手动延迟必须与请求一致。
数值参考不调用供应商 C 模型，也不读取实际输出来生成期望值。
依据：[非阻塞模式](https://docs.amd.com/r/en-US/pg104-cmpy/NonBlocking-Mode)、
[延迟设置](https://docs.amd.com/r/en-US/pg104-cmpy/Core-Latency)。

## 范围

常用配置 8 组，大矩阵 17070 组独立参数。包括 8 至 63 位分量、LUT/DSP、
资源/性能选择、组合/自动/长流水线、时钟使能、截断/舍入、TLAST 和 TUSER。
每组包含边界组合、连续输入、通道有效信号错开、暂停和流水线排空。
报告中的 `reference_sequence_events` 是输入序列计数，不是芯片内部覆盖率。

尚未接入 Blocking、复位和浮点模式。复位至少持续两拍，且内部会再寄存一拍，
不能把单拍随机翻转当作合法复位测试。
本机 Artix-7 也不能代表支持浮点 DSP 的其他器件。
依据：[端口与复位](https://docs.amd.com/r/en-US/pg104-cmpy/Port-Descriptions)、
[数据类型限制](https://docs.amd.com/r/en-US/pg104-cmpy/Data-Type-Options)。

大矩阵只检查了配置约束并抽取代表参数实测，没有全部运行；不保证每个组合都能创建。
已复现一项[手动长延迟异常](latency_issue.md)，对应配置保留失败，不代表检查器损坏。

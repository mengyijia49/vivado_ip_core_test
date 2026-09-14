# Divider 数值自检

官方 demo 不比较商和余数。框架另生成一份参数化 VHDL testbench，
用 Python 参考模型的结果逐项检查 IP 输出。

## 怎么计算期望值

```text
quotient  = trunc(dividend / divisor)
remainder = dividend - quotient * divisor
```

有符号除法向零截断，不能直接用 Python 的 `//` 代替。
商按被除数位宽编码，余数按除数位宽编码；输出高位是商，低位是余数，
负值使用补码。

当前排除除数为零，以及最小负数除以 -1 的商溢出情况。
尚未为这两类情况定义并验证期望输出。

## 怎么送入和检查

testbench 同周期送入被除数和除数，并成对拉高 tvalid。
输出有效时，按顺序比较整个 `dout_tdata`，同时检查：

- 输出 tvalid 的每个周期位置是否符合输入有效序列和 XCI 时延。
- 结果、顺序和数量是否正确，有没有未知位或额外输出。
- 是否在输入周期加流水线排空的超时范围内结束。

探索模式可以打乱输入、插入有效信号间隔或突发段。
`gaps.txt` 记录间隔，`schedule.json` 记录事务与原始向量的对应关系。

通过标记为 `DIVIDER_SELF_CHECK_STATUS: PASS`，失败标记为
`DIVIDER_SELF_CHECK_STATUS: FAIL`。XSim 成功后，Python 再逐行比较期望和实际文件；
使用的是同一份期望值，不是第二个参考模型。

## 配置和文件

默认三组输入数为：`divider_u16_u8` 44 个、`divider_u32_u16` 44 个、
`divider_s16_s8` 48 个。输入含边界、整除/非整除、符号组合和固定种子随机值。
参数范围见[配置说明](configuration.md)，端口见[接口说明](protocol.md)。

每批文件位于 `runs/batches/<run_id>/divider/<case_id>/`：

```text
manifest.json                 参数、XCI、工具和文件哈希
tb/tb_divider_selfcheck.vhd
vectors/input_vectors.txt
vectors/expected_output.txt
vectors/vectors.json
vectors/gaps.txt
vectors/schedule.json
outputs/actual_output.txt
outputs/failure.json          失败时生成
```

输入输出均为位串文本，便于查看和逐行比较。

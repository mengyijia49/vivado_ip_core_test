# Divider 接口

本文对应 `divider_u16_u8`：16 位无符号被除数、8 位无符号除数，
整数商加余数、NonBlocking、无复位和使能。

依据是生成工程中的三份文件。相对于
`runs/batches/<run_id>/divider/divider_u16_u8/proj/`：

```text
divider_ip_test.gen/sources_1/ip/div_gen_0/demo_tb/tb_div_gen_0.vhd
divider_ip_test.gen/sources_1/ip/div_gen_0/sim/div_gen_0.vhd
divider_ip_test.srcs/sources_1/ip/div_gen_0/div_gen_0.xci
```

## 全部端口

| 端口 | 方向 | 位宽 | 用途 |
| --- | --- | ---: | --- |
| `aclk` | 输入 | 1 | 时钟 |
| `s_axis_dividend_tvalid` | 输入 | 1 | 被除数有效 |
| `s_axis_dividend_tdata` | 输入 | 16 | 被除数 |
| `s_axis_divisor_tvalid` | 输入 | 1 | 除数有效 |
| `s_axis_divisor_tdata` | 输入 | 8 | 除数 |
| `m_axis_dout_tvalid` | 输出 | 1 | 结果有效 |
| `m_axis_dout_tdata` | 输出 | 24 | 商和余数 |

没有外部 reset。封装内部的 `aresetn` 固定为 1，XCI 中 `ARESETN=false`。

接口使用 AXI-Stream 风格的 tvalid/tdata，但当前没有 tready，
也没有 tlast、tuser、tkeep、tstrb。不能等待 ready，也不能施加输出反压。
两路输入同时有效时提交一对除法操作数。

输出低 8 位是余数，高 16 位是商，XCI 记录时延为 18 个周期。
其他配置的位宽和时延要重新读取 XCI，不能照搬这组数值。

## 官方 demo 做什么

demo 产生 100 ns 周期的时钟。被除数使用逐位移动的单比特数据，
除数的最低位始终为 1，因此不会除零。

输入先连续有效，再分别插入被除数间隔和两通道各自的间隔。
它在上升沿后延迟 `T_HOLD` 更新输入，在上升沿后延迟 `T_STROBE` 采样输出。
某通道有效时推进其数据索引，无效时把该通道数据置零。

输出有效时，demo 检查数据是否含未知值，但不计算或比较商和余数。
没有检测到错误就于固定测试周期结束，报告 `Test completed successfully`。
它用 `severity failure` 结束，因此这条消息中的 Failure 不表示测试失败。

## 换成文件输入时保留什么

- 继续产生时钟，在采样沿保持数据稳定。
- 常规数值测试把两路 tvalid 成对置高；插入间隔时成对置低。
- 只在输出 tvalid 为高时读取结果，每个有效输出都要接收。
- 按当前配置拆分商和余数，记录输出顺序和数量。
- 输入结束后等待流水线排空，设置超时并检查额外或缺失输出。

当前框架已经使用文件驱动自检，文件是逐行的二进制位串文本，
不是 `input.bin` 原始二进制文件。具体判定见[数值自检](selfcheck.md)。

# AXIS Protocol Checker：没有启用 TSTRB，却多报了它的变化错误

Vivado 2026.1 的 `axis_pc_128_partial` 配置中，测试故意在等待接收时改变 TKEEP，
检查器正确报出 TKEEP 变化，但同时多报了 TSTRB 变化。该配置没有启用 TSTRB。

## 这个 IP 不算数字，它检查传输是否守规则

AXI4-Stream 用来逐笔传数据。发送端给出数据和有效信号，
接收端表示是否准备好，两边都同意才完成一次传输。

Protocol Checker 在旁边观察这些信号，发现违反规则就设置相应状态位。
所以本次测试会故意制造违规：要检查它有没有报对错误，而不是要求所有状态都为 0。

| 信号 | 含义 |
| --- | --- |
| TVALID | 发送方提供了一笔有效数据 |
| TREADY | 接收方现在能接收 |
| TKEEP | 每个字节是否属于有效传输内容，1 位对应 1 字节 |
| TSTRB | 配合 TKEEP 区分数据字节与位置字节；本配置未启用 |
| TLAST | 这笔是否为包尾 |
| TDEST / TID / TUSER | 目的标记、流标识、用户附加信息 |

在 TVALID=1、TREADY=0 时，一笔数据正等着被接收。
发送端应保持这笔数据及相关标记，不能把它悄悄换成另一笔。

## 本次全部参数

目前这一现象只有下面一组配置记录：

| 参数 | 值 | 含义 |
| --- | --- | --- |
| `data_bytes` | 16 | 每拍 16 字节，也就是 128 位数据 |
| `has_tready` | true | 检查接收方的准备信号 |
| `has_tkeep` | true | 检查 16 位字节有效标记 |
| `has_tstrb` | false | 不启用 TSTRB 检查接口 |
| `has_tlast` | true | 检查包尾标记 |
| `tdest_width / tid_width / tuser_width` | 8 / 0 / 16 | 目的标记 8 位，不带 TID，用户信息 16 位 |
| `max_waits` | 64 | 等待准备信号的监测阈值 |
| `has_aclken` | false | 不带额外时钟使能端口 |
| `has_system_reset` | false | 不带独立系统复位；接口本身仍有 aresetn 复位 |

## 故意制造的违规是什么

testbench 先复位检查器，再建立 TVALID=1、TREADY=0 的等待状态。
TKEEP 起初全为 0，随后把最低一位改成 1，而接收方还没有同意接收。
这故意违反了等待期间 TKEEP 应保持不变的规则。

```text
有效数据正在等待接收：TVALID=1，TREADY=0
    ↓
TKEEP 从 0x0000 变为 0x0001
    ↓
应报告 TKEEP 变化错误
    ↓
实测还多报了 TSTRB 变化错误
```

## 0x08 和 0x48 具体是什么意思

状态字里的每一位代表一种检查结果，不是一个普通数值结果。
[PG145 表 2-4](https://docs.amd.com/api/khub/documents/SLWzYbqIew1c8Si3gFkbjA/content)
及本项目参考定义中，第 3 位对应 TKEEP 保持检查，第 6 位对应 TSTRB 保持检查：

| 状态 | 置 1 的位 | 含义 |
| --- | --- | --- |
| 参考 `0x00000008` | 第 3 位 | 只报 TKEEP 变化 |
| 实测 `0x00000048` | 第 3 位和第 6 位 | 同时报 TKEEP 和 TSTRB 变化 |

`0x48 = 0x08 + 0x40`，多出的 `0x40` 就是第 6 位。
手册把该项检查列为 TSTRB 等接口信号启用时才有效，因此这里值得追查。

输出序号 5、14、23 都出现这个结果。它们是同一场景在测试序列中重复运行，
不是三组参数，也不是三个已经确定的 bug。

## 还需要排查什么

下一步要用固定的少量时钟步骤复现，并核对生成模型如何处理未启用的 TSTRB。
例如内部是否由其他信号派生了它，或者配置没有按预期生效。
当前还没有这份独立复现，不能仅据此确定检查器的内部原因。

[失败字段](../../../evidence/vivado_2026_1/full_regression/2026-09-22_12-47-30_UTC+0800_4bca4f69/axis_protocol_checker/partial_failure.json)
保存期望与实测状态，
[场景列表](../../../evidence/vivado_2026_1/full_regression/2026-09-22_12-47-30_UTC+0800_4bca4f69/axis_protocol_checker/partial_scenarios.json)
给出序号对应的测试内容。

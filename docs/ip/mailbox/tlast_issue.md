# Mailbox：数据传过去了，表示“这一包结束”的标记却丢了

Vivado 2026.1 的四组 Mailbox 流接口配置中，输入某笔数据的 `TLAST=1`，
对应输出却为 0。数据和握手检查能够完成，报错集中在包尾标记。

## Mailbox 在这里做什么

Mailbox 用于两个模块之间交换数据。可以把它理解成两条相反方向的队列：
一侧写入，对侧按顺序取出。先进入的先出来，这种队列叫 FIFO。

本次选择的是 AXI4-Stream 接口，不是通过地址逐个读写寄存器的方式。
数据沿流接口一笔一笔传递：

```mermaid
flowchart LR
    A["一侧发送端"] --> Q["Mailbox 内部队列"]
    Q --> B["另一侧接收端"]
```

每个方向都有一条这样的路径，测试也包含两个方向同时传输的情况。

## 接口上的几个信号

| 信号 | 用人话解释 |
| --- | --- |
| TDATA | 这笔传输携带的数字 |
| TVALID | 发送方说“这笔数据有效，可以接收” |
| TREADY | 接收方说“我现在可以接收” |
| TLAST | 这笔是当前数据包的最后一笔 |

在时钟采样时，TVALID 和 TREADY 同时为 1，才算完成一笔传输。
接收端暂时让 TREADY=0 就是回压，表示“先别交给我，等一下”。

比如为了说明包尾的作用，假设一个包由 10、20、30 三笔数据组成：

| 数据 | 应配的 TLAST |
| --- | ---: |
| 10 | 0 |
| 20 | 0 |
| 30 | 1 |

这里的 10、20、30 只是解释接口的例子。
若最后那笔的 TLAST 丢了，接收方即使拿到三个正确数字，
也可能继续等待包尾，无法知道这一包已经结束。

## 四组实际失败的参数

四组都使用 32 位数据、同步时钟、AXI4-Stream 接口。
32 位表示每笔可携带 4 字节。深度表示内部能排队的字数，
不是一个包必须有多少笔。

| 配置 | 队列深度 | 存储实现 | 现有记录 |
| --- | ---: | --- | --- |
| `mailbox_axis_d16_distributed` | 16 | Distributed_RAM，分布式存储资源 | 专项重跑和整批自检 |
| `mailbox_axis_d32_distributed` | 32 | Distributed_RAM | 整批自检 |
| `mailbox_axis_d32_block` | 32 | Block_RAM，专用块存储资源 | 专项重跑和整批自检 |
| `mailbox_axis_d64_block` | 64 | Block_RAM | 整批自检 |

两种 RAM 是内部用什么资源保存队列数据的选择。
`async_clocks=false` 表示本次没有测试两个独立异步时钟之间的传输。
四组都由现有流接口自检 testbench 运行；专项重跑使用的也是框架生成的
`tb_mailbox_axis_selfcheck`，不要把它误认为另一份独立手写 testbench。

## 实测与预期

| 检查内容 | 预期 | 实测 |
| --- | --- | --- |
| 一笔已接收输入的包尾标记为 1 | 对应输出的包尾也应为 1 | 输出为 0 |
| 数据与传输握手 | 数据按检查规则到达，传输完成 | 这些检查完成 |
| 换深度和 RAM 类型 | 查看现象是否消失 | 四组仍有 TLAST 报错 |

日志原文为 `MAILBOX_AXIS_TLAST_MISMATCH actual='0' expected='1'`，
也记录了双向并发传输时的差异。单凭端口存在还不足以完全确定产品承诺，
下一步需要厂商确认该模式是否应保留输入 TLAST，以及为何当前模型输出为 0。

本批 `failure.json` 的第一项误指向了 `RESET` 文本，
所以本页的 TLAST 结论依据原始仿真日志。
[深度 16 分布式 RAM 日志](../../../evidence/vivado_2026_1/observations/2026-09-22_12-13-24_UTC+0800_e52ddfa9/mailbox/d16_distributed_sim.process.log)
和[深度 32 块 RAM 日志](../../../evidence/vivado_2026_1/observations/2026-09-22_12-13-24_UTC+0800_e52ddfa9/mailbox/d32_block_sim.process.log)
保留了专项重跑结果；四组完整参数见[整批报告](../../../evidence/vivado_2026_1/full_regression/2026-09-22_12-47-30_UTC+0800_4bca4f69/report.csv)。

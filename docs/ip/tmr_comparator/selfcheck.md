# TMR 比较器自检

```bash
python3 scripts/run_all.py --ip-type tmr_comparator
python3 scripts/run_all.py --config configs/ip/tmr_comparator/extended.json --list-cases
```

## 检查方法

三路模式检查 1–2、1–3、2–3 的差异，对应 Compare 的 bit 0、1、2。
开启投票自检后，额外输入 Discrete 应等于逐位多数值；不相等时 bit 3 告警。
旁路开启时，自检改为比较第一路与 Discrete，但两两比较仍继续工作。
双路锁步模式只有两路输入，Compare 是一位向量。

Python 独立计算多数值和差异。定向输入逐位改变各副本，并逐位破坏外部投票值，
检查漏报和误报。一位配置穷举所有输入；宽配置还覆盖多位同时不同和随机值。
参考模型不从仿真结果反推期望值。

## 参数和端口

- `width`：框架支持 1–1024 位离散输入。
- `triple`：三路或双路；`voter_check` 仅用于三路。
- `disable_port`：仅在投票自检开启时接入，避免无作用的参数组合。
- `include_mask`：64 位整数，低 64 位按掩码比较，更高位始终参与比较。
- `input_register`：开启后有 Clk 和同步高有效 Rst，复位后的告警为零。

输入寄存模式在上升沿后检查当前采样输入的结果。当前还未检查两沿之间的保持行为。
没有开启寄存器时，无时钟和复位端口。
所有 Compare 位均严格校验，包括零值、未知值和复位期间的值。

## 范围和依据

只接入离散信号，不含总线、时间冗余和内置测试注入接口。
这是 IP 本身的功能仿真，不代表整个容错系统或硬件实现已经得到验证。

比较规则依据 [PG268 比较器说明](https://docs.amd.com/r/en-US/pg268-tmr/TMR-Comparator?contentId=ukIGPedf3GJyt6KXi9qRIA)。
告警位序、掩码及端口开关还核对了本机 2025.2 的可读接口实现和 XCI；
仓库中不包含厂商源码。实测记录见[接入检查](../../experiments/tmr_acceptance.md)。

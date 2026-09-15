# TMR 投票器自检

```bash
python3 scripts/run_all.py --ip-type tmr_voter
python3 scripts/run_all.py --config configs/ip/tmr_voter/extended.json --list-cases
```

## 检查方法

只接入离散信号接口。三路模式逐位取多数值，不是从三个完整输入字中挑一个。
`TMR_Disable=1` 时输出第一路；双路锁步模式也输出第一路。
开启内置比较器后，同时检查两两不一致的告警，不能只检查投票结果。
参考值由 Python 数位计票和整数比较得到，不读取 DUT 输出作为期望值。

每一位都安排三路输入的八种组合，并切换其余位为全零、全一。
另有跨位差异、多路不同、旁路切换和随机输入。一位配置穷举完整输入空间。
这些故障输入只是给 IP 的正常功能激励，不会修改 IP 内部逻辑。

## 参数和端口

- `width`：1–1024 位，这是框架接入范围，不是厂商公布的最大值。
- `triple`：三路投票或双路锁步。
- `disable_port`：仅三路模式启用 `TMR_Disable`。
- `comparator`、`voter_check`：内置比较器和投票自检。
- `input_register`：比较输入寄存；投票数据本身仍为组合输出。
- `include_mask`：64 位整数，控制低 64 位是否参与比较；更高位仍参与比较。

本机生成端口中，`Discrete1/2/3` 和 `Discrete` 都是向量，包括一位配置。
有比较器时 `Compare` 始终为四位。三路模式 bit 0/1/2 分别比较 1–2、1–3、2–3，
bit 3 检查投票输出。锁步模式只定义 bit 0，其他三位不作功能判断，原始值仍保存。
不启用比较器时没有 Compare。启用输入寄存器时有 Clk，但当前模式没有 Rst。
不要直接套用独立 TMR Comparator 的复位端口。

## 范围和依据

所有已定义输出位都参与比较，不使用“无 ERROR 就通过”的判断。
当前只在组合稳定后或时钟上升沿后采样，尚未检查寄存器在两个时钟沿之间的保持行为。
没有接入时间冗余、AXI/LMB/BRAM 接口或内置测试注入接口，也不进行综合后的测试。

功能依据 [PG268 投票器说明](https://docs.amd.com/r/en-US/pg268-tmr/TMR-Voter?contentId=spWYQjbdzOIg7qRCl0tDdQ)。
端口开关、告警位序和离散掩码同时核对本机 2025.2 的 `component.xml`、生成 XCI
及随安装提供的可读接口实现；这些厂商文件不复制进仓库。
实测记录见[接入检查](../../experiments/tmr_acceptance.md)。
锁步加内置比较器目前有[厂商模型内部端口展开失败](lockstep_issue.md)，
不能将该模式列为已通过功能仿真；配置和失败记录保留用于复现。

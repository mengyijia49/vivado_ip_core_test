# FIR 接入前检查

2026-09-15，本机 Vivado 2025.2、Artix-7、FIR Compiler 7.2 revision 26。
目前完成参数探测和[全精度边界的独立复现](full_precision_issue.md)，还不是常规流水线插件。

## 已读到的接口

Single_Rate、Real、单通道、单路径，启用复位、READY、Packet_Framing 和 7 位 USER 时：

| 端口 | 方向 | 本次位宽 |
| --- | --- | --- |
| `aclk`、`aresetn` | 输入 | 各 1 |
| `s_axis_data_tvalid`、`s_axis_data_tlast` | 输入 | 各 1 |
| `s_axis_data_tready` | 输出 | 1 |
| `s_axis_data_tdata`、`s_axis_data_tuser` | 输入 | 8、7 |
| `m_axis_data_tvalid`、`m_axis_data_tlast` | 输出 | 各 1 |
| `m_axis_data_tready` | 输入 | 1 |
| `m_axis_data_tdata`、`m_axis_data_tuser` | 输出 | 16、7 |

这些不是所有 FIR 配置的固定端口。数据按字节补齐，实际数值位宽需另查 XCI。
接入时须按每个已握手输入更新历史，空闲周期和回压都不能推进卷积状态。
[PG149 TLAST](https://docs.amd.com/r/en-US/pg149-fir-compiler/TLAST-Options)
中的 Packet_Framing 是包边界，不是清空历史的命令。
[复位规则](https://docs.amd.com/r/en-US/pg149-fir-compiler/Resets)
区分控制复位与数据历史复位，不能把 Reset_Data_Vector 关闭时也按清零建模。

## 参数探测

记录：`reports/framework/fir_probe/2026-09-15_14-40-59_UTC+0800_d0b08eb9/summary.json`。
十组请求中八组创建成功，包含正负及全零系数、两种架构、有符号和无符号数据、对称系数及偶数舍入。
这里只确认创建和实际参数，不代表八组都做完功能自检。

- 49 位数据请求被本机 Artix-7 配置拒绝，提示有效范围 2 至 35；其他器件未据此限死。
- 一个系数被拒绝，最少为两个；`[-8,0,0]` 保留三个抽头，只是其中两个为零。
- Integer_Coefficients 下，全非负系数自动选 Unsigned，有负系数才选 Signed。
- `RateSpecification` 实际接受 Frequency_Specification、Input_Sample_Period、Output_Sample_Period。
  安装 XML 里另有的 Hardware_Oversampling_Rate 在这条配置入口被拒绝。
- Full_Precision 自动选择结果位宽，仍需独立核对合法输入的正负极值是否能表示。

首次批次 `2026-09-15_14-39-34_UTC+0800_0aaa9073` 因公共速率枚举不合法，十项均失败。
失败后留下的默认 XCI 不能当成请求配置已被接受。
早期正系数对照也因预期 Signed 与实际 Unsigned 不符而停止，修正后才完成仿真。
这些配置与检查程序问题不计作厂商功能 bug。

## 最后一次探测

批次 `2026-09-15_15-31-49_UTC+0800_c7d370c8` 的八项创建和参数核对通过：
35 位数据及系数的两种架构、2 位最小输入、16 位负系数、全零系数、混合系数、
9 位输入及 129 个抽头。运算间隔包含 1、2、3、8、16、64 周期。
这批只检查创建，没有运行数值自检，也没有加入配置矩阵。

## 收尾范围

按使用者要求，本轮停止扩充 IP 和参数，不继续接入 FIR 常规插件。
保留独立复现及其正常对照，不增加目前的 36 类常规 IP 数量。

以下仅记录未完成的覆盖，不是自动继续执行的任务：

- 常规卷积参考及参数化 testbench 尚未接入统一流水线。
- 舍入、抽取、插值、多通道、系数重载、ACLKEN 和运行中复位未做完整功能测试。
- 全精度位宽不足的异常仍待厂商确认，不能通过截断参考结果让用例 PASS。

已有复现命令和完整检查结果见[问题记录](full_precision_issue.md)。

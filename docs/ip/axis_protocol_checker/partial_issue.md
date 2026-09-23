# AXIS Protocol Checker：已查明额外状态位来自默认信号

2026-09-23 已完成排查。这条不再作为 IP bug 候选。
`axis_pc_128_partial` 没有 TSTRB 端口，但协议规定：没有 TSTRB 时，内部默认用 TKEEP。
因此等待期间改变 TKEEP，也改变了内部的 TSTRB；报出两个变化状态有依据。
原先“只应该报一个”的参考值不完整，已修正。

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
| TSTRB | 配合 TKEEP 区分数据字节与位置字节；本配置无端口，内部默认等于 TKEEP |
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
| `has_tstrb` | false | 不带外部 TSTRB 端口；不是内部信号固定为 0 |
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
TKEEP 变化，内部默认的 TSTRB 也一起变化
    ↓
实测同时报告两种变化，状态为 0x48
```

## 0x08 和 0x48 具体是什么意思

状态字里的每一位代表一种检查结果，不是一个普通数值结果。
[PG145 表 2-4](https://docs.amd.com/api/khub/documents/SLWzYbqIew1c8Si3gFkbjA/content)
及本项目参考定义中，第 3 位对应 TKEEP 保持检查，第 6 位对应 TSTRB 保持检查：

| 状态 | 置 1 的位 | 含义 |
| --- | --- | --- |
| 旧参考 `0x00000008` | 第 3 位 | 漏算了默认 TSTRB 的变化 |
| 实测及修正后参考 `0x00000048` | 第 3 位和第 6 位 | 同时报 TKEEP 和 TSTRB 变化 |

`0x48 = 0x08 + 0x40`，多出的 `0x40` 就是第 6 位。
此前只按手册的检查使能说明理解，没有考虑缺省信号的处理，所以误判为额外告警。

输出序号 5、14、23 都出现这个结果。它们是同一场景在测试序列中重复运行，
不是三组参数，也不是三个已经确定的 bug。

## 为什么这样判断

[Arm AXI-Stream 规范 IHI 0051B 第 3.1.2 节](https://documentation-service.arm.com/static/64819f1516f0f201aa6b963c)
明确规定，TSTRB 缺省时等于 TKEEP。它不是被忽略，也不是固定为零。
Vivado 2026.1 安装的 `axis_protocol_checker_v2_0_rfs.v` 第 745 行实现了这个选择；
文件在 `/data/Xilinx/2026.1/Vivado/data/ip/xilinx/axis_protocol_checker_v2_0/hdl/`。

另外写了一个不调用 Python 参考模型的 VHDL 小测试，数据宽度为 1 字节，
开启 TREADY、TKEEP，关闭其他侧带、ACLKEN 和系统复位，MAX_WAITS=0。
两组配置只改变 TSTRB 是否启用。每个场景先复位，等待期间在时钟下降沿改变信号：

| 场景 | 无 TSTRB 端口 | 有 TSTRB 端口 |
| --- | --- | --- |
| 等待期间所有信号保持 | `0x00` | `0x00` |
| 只把 TKEEP 从 0 改成 1 | `0x48` | `0x08` |
| TKEEP 和测试端 TSTRB 都从 0 改成 1 | `0x48` | `0x48` |
| TKEEP 保持 1，只改变测试端 TSTRB | `0x00`，该信号没有接入 IP | `0x40` |

上表 8 项实测都与固定期望一致。合法输入没有被误报；额外的 bit 6 恰好取决于
内部 TSTRB 是否跟随 TKEEP。这是本次排除误报的关键对照。

框架现在按配置计算完整的 32 位期望状态，不屏蔽 bit 6。
原配置修正前后场景文件和实际输出完全相同，只修正期望值。
全部 6 组常用配置、18 个阶段复测均 PASS。没有因此宣称所有协议检查场景都正确。

## 复跑与证据

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type axis_protocol_checker
VIVADO_INTEGRATION=1 PYTHONPATH=src:tests python3 -m unittest \
  integration.ip.axis_protocol_checker.test_optional_strb -v
```

本次[修改前报告](../../../evidence/vivado_2026_1/axis_protocol_checker/protocol_review/2026-09-23_16-16-05_UTC+0800_21e595ba/report.json)、
[修改后报告](../../../evidence/vivado_2026_1/axis_protocol_checker/protocol_review/2026-09-23_16-17-52_UTC+0800_46625706/report.json)、
[独立 VHDL 对照](../../../evidence/vivado_2026_1/axis_protocol_checker/protocol_review/2026-09-23_16-20-22_UTC+0800_e1f9e2ab/)
已归档，包含各配置的参数、testbench、观察值和日志。

以下是最初误判时的历史记录，保留原样：

[失败字段](../../../evidence/vivado_2026_1/full_regression/2026-09-22_12-47-30_UTC+0800_4bca4f69/axis_protocol_checker/partial_failure.json)
保存期望与实测状态，
[场景列表](../../../evidence/vivado_2026_1/full_regression/2026-09-22_12-47-30_UTC+0800_4bca4f69/axis_protocol_checker/partial_scenarios.json)
给出序号对应的测试内容。

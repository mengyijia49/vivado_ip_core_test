# AXIS Protocol Checker 自检

## 检查方法

这个 IP 只观察 AXI4-Stream 信号，不转发数据。发现协议违规后，它会把对应状态位置 1，
并保持到复位。测试每次先复位检查器，再发送一个独立场景，最后精确比较全部 32 位
`pc_status`，不是只看 `pc_asserted`。

Python 参考按公开规则给出每个场景应置的状态位。当前检查以下情况：

- 复位释放后的第一拍不能拉高 `TVALID`。
- 回压期间 `TDATA`、`TID`、`TDEST`、`TKEEP`、`TSTRB`、`TLAST` 和 `TUSER` 必须稳定。
- `TVALID` 拉高后必须保持到握手。
- 等待 `TREADY` 不能超过配置上限，`ACLKEN=0` 时暂停等待计数。
- `TKEEP=0` 的字节通道不能同时让 `TSTRB=1`。

只有配置中实际存在的端口才安排相应场景。启用独立 `system_resetn` 时，检查器先等待内部
三级同步释放，此时不会观察 `aresetn` 的释放边沿，因此该配置不声称覆盖第一条规则。
没有外部 TSTRB 端口时，内部默认 TSTRB=TKEEP；因此 TKEEP 在回压时变化会同时触发
bit 3 和 bit 6。参考按配置计算两个状态位，不忽略其中任何一位。

## 参数和运行

常用回归有 6 组。可选矩阵有 65536 组，覆盖 1/4/16/128 字节数据、可选侧带、
`ACLKEN`、系统复位和 0/16/64/256 拍等待上限。矩阵只做了静态参数校验，没有全部运行。

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type axis_protocol_checker
```

只运行一个宽边界配置：

```bash
python3 scripts/run_all.py --ip-type axis_protocol_checker --case axis_pc_1024_full
```

## 2026.1 结果

478 组全量运行包含这类 IP 的 6 组常用配置。`axis_pc_no_ready_sidebands`
最初在 testbench 生成阶段失败：Vivado 把没有 `TREADY` 的配置的 `MAX_WAITS`
固定为 0，而框架仍期望 256。适配后，该组三阶段复测通过。
`axis_pc_128_partial` 原先多出的 bit 6 已查明来自默认 TSTRB=TKEEP，属于参考漏算。
2026-09-23 修正参考后，全部 6 组常用配置、18 个阶段通过。
另有独立 VHDL 对照，分别启用和关闭 TSTRB，8 项观察均符合固定期望。
这条已排除出 IP bug 候选，见[排查记录](partial_issue.md)。
原始输入输出和两次报告见[全量运行记录](../../experiments/vivado_2026_full_regression.md)。

可选大矩阵仍未全部运行。

## 当前限制

没有接入可选 AXI-Lite 状态读取接口，也没有发送未知值 `X`。稀疏 `TKEEP` 的厂商扩展
告警不是 `pc_status` 规则，本次不检查。控制寄存器、未知值和扩展告警不能用现有 PASS
代替。

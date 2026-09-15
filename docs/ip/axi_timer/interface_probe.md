# AXI Timer 接口探测

2026-09-15，Vivado 2025.2，`axi_timer:2.0` 修订 37。
编号 `2026-09-15_03-33-40_UTC+0800_20846133`。
8 位、双计数器、非级联配置创建成功，尚未接入功能自检。

工程在 `runs/framework/catalog/<编号>/axi_timer/timer8/`，
日志在 `runs/logs/framework/catalog/<编号>/axi_timer/timer8/`。
参数和实际调用命令分别保存为 `parameters.json`、`create.invocation.json`。

AXI-Lite 数据为 32 位，地址为 5 位，WSTRB 为 4 位；没有 AWPROT、ARPROT。
时钟为 `s_axi_aclk`，复位为低有效 `s_axi_aresetn`。
另有 `capturetrig0/1`、`freeze` 输入，`generateout0/1`、`pwm0`、`interrupt` 输出。
实际模型参数 `C_COUNT_WIDTH=8`、`C_ONE_TIMER_ONLY=0` 已与 XCI 核对。

PG079 也规定忽略 WSTRB，写地址和数据的 VALID 同时发出。
每个计数器有控制、加载、计数寄存器；保留地址返回 OKAY、读零、写入无效。
见[寄存器说明](https://docs.amd.com/r/en-US/pg079-axi-timer/Register-Space)。

下一步复用公共 AXI-Lite 驱动，但计数、加载、中断清除等规则由独立模型实现。
先检查小位宽的上下计数、边界回绕、暂停、重装载和一次触发，
再补捕获、PWM 和级联。不能直接用原生计数器参考代替总线外设的完整状态。

## 补充探测

编号 `2026-09-15_09-30-19_UTC+0800_20a29142`，以下三组创建成功，仍未功能自检：

- `timer32_single_low`：32 位单计数器，捕获和生成输出均低有效。
- `timer16_dual_mixed`：16 位双计数器，两路使用不同的触发及输出极性。
- `timer64_cascade`：64 位模式，实际模型仍是两个 32 位计数器。

同批 `timer9_rejected` 被 Catalog 拒绝，错误 `IP_Flow 19-3461` 明确列出有效位宽为 8、16、32。
不能把本机参数描述中的“8 至 32”解释成其间所有整数，也不能把这个拒绝计作 IP bug。
这与 [PG079 的配置选项](https://docs.amd.com/r/en-US/pg079-axi-timer/Configuring-the-Core-Parameters)一致。
级联接入还需检查 TCSR0 的 CASC 位及跨计数器进位，创建成功不代表已经完成该项功能测试。

## 固定计数窗口

独立 VHDL 为 `tests/fixtures/ip/axi_timer/tb_timer_probe.vhd`，不调用 Python 数值模型。

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
PYTHONPATH=src VIVADO_INTEGRATION=1 python3 -m unittest discover -s tests -p 'test_timer_probe.py' -v
```

`2026-09-15_10-07-37_UTC+0800_81a4720d` 完成探测。
在 8 位双计数器中，解除暂停 1、2、3、4 个时钟后，165 依次变为 166、168、171、175；
暂停和关闭 ENT 后保持不变。忽略 WSTRB、显式加载、只读 TCR 和保留地址的检查也通过。

从 3 向下自动重装载，连续运行的脉冲间隔为 5 个时钟。
每次只运行一个时钟并暂停，计数读回为 2、1、0、3：回绕后的重装载不受暂停阻止。
单次模式回绕后停在 255，清除中断再运行仍保持。
捕获保持模式先得到 64，未读 TLR 时的后续触发不覆盖；读后再触发可捕获 71。
ENALL 同时启动两路，运行 7 个时钟后分别从 10、20 变成 17、27。

工程在 `runs/framework/timer_probe/<编号>/axi_timer/`，日志在同类 `runs/logs/framework/` 下，
寄存器和脉冲观测在 `reports/framework/timer_probe/<编号>/summary.json`。
最初编号 `2026-09-15_10-05-31_UTC+0800_005654b0` 因探测代码的 VHDL 重载歧义编译失败，
修正了显式类型后重跑，原记录保留。这不是 IP 故障。

# AXI GPIO 接口探测

2026-09-15，Vivado 2025.2，`axi_gpio:2.0` 修订 37。
编号 `2026-09-15_03-33-40_UTC+0800_20846133`。
三组模型创建成功，当时尚未接入功能自检。
后续已接入，当前范围见[自检说明](selfcheck.md)。

| 配置 | 接口 |
| --- | --- |
| mixed1 | 单通道 1 位双向，无中断 |
| dual_odd_interrupt | 双通道 7/31 位双向，有中断，非零初始数据和方向 |
| fixed_io | 通道 1 为 32 位只输入，通道 2 为 1 位只输出，有中断 |

工程在 `runs/framework/catalog/<编号>/axi_gpio/<配置>/`，
日志在 `runs/logs/framework/catalog/<编号>/axi_gpio/<配置>/`。
各目录的 `parameters.json` 保存参数，`create.invocation.json` 保存完整创建命令。

AXI-Lite 数据为 32 位，地址为 9 位，WSTRB 为 4 位；没有 AWPROT、ARPROT。
时钟是 `s_axi_aclk`，复位是低有效 `s_axi_aresetn`。
双向口分成 `_io_i`、`_io_o`、`_io_t`，不是 VHDL inout。
只输入、只输出配置会删去不用的端口，1 位 GPIO 仍是向量。

## 参考模型不能忽略的区别

PG144 明确说明此 IP 忽略 WSTRB，写入时 AWVALID 和 WVALID 应同时发出。
未实现寄存器读零、写入无效；中断状态采用写 1 翻转，不是普通写 1 清除。
这些是已公开的规则或限制，不能按通用寄存器假设直接报成新 bug。
见[寄存器说明](https://docs.amd.com/r/en-US/pg144-axi-gpio/Register-Space)。

PG144 的 [DATA 页](https://docs.amd.com/r/en-US/pg144-axi-gpio/AXI-GPIO-Data-Register-GPIOx_DATA)
仍写输出位读零，但生成 IP 附带的官方变更记录明确记载：2017.1、修订 14 增加了输出数据读回。
本机为修订 37，参考模型据此检查输出读回；不能只读手册这一页就报新 bug。
变更记录随本批产物归档，更多版本差异见[寄存器问题记录](register_issue.md)。

公共 AXI-Lite 请求、响应和回压检查现已接入，另有本 IP 的寄存器状态模型。
已安排方向切换、复位默认值、未实现通道、中断置位/翻转/屏蔽场景。
输入引脚变化到寄存器、中断的延迟仍需核对，不以实测值反向拟合参考模型。
中断输入至少保持一个 AXI 时钟周期；状态位支持软件翻转置位和清除，
可先用这个规则独立检查屏蔽逻辑。见[中断寄存器](https://docs.amd.com/r/en-US/pg144-axi-gpio/IP-Interrupt-Enable-IPIER-and-IP-Status-Registers-IPISR?contentId=OKHFKf9Vcear3gmbPHFrzA)。

# Catalog 候选记录

2026-09-14 在本机 Vivado 2025.2、Artix-7 配置下探测。
编号：`2026-09-14_22-20-30_UTC+0800_ee015e6d`。
产物在 `runs/framework/catalog/<编号>/<IP>/`，日志在对应的 `runs/logs/framework/catalog/`。

## 已确认能创建默认 IP

本轮 22 项均能创建默认模型。这只是 Catalog 探测，没有运行功能测试，
不能据此列为框架已支持，更不能推定全部参数可用。

| 候选 | 当前还需要的工作 |
| --- | --- |
| axis_register_slice、axis_data_fifo、axis_clock_converter | 已接入行为自检，补充部分字节、运行中复位和时钟场景 |
| fifo_generator | 已接入同钟标准读、FWFT、计数及常量阈值；待补独立时钟、异宽、阈值输入和 ECC |
| blk_mem_gen | 已接入同钟 RAM、字节写、输出寄存和有效位判断，待补异宽、独立时钟和 ECC |
| xbip_multadd | 已接入组合、流水线、PCIN 和输出截取，待补更多时序组合 |
| cmpy | 已接入非阻塞整数模式，待补 Blocking、复位和更多实现选择 |
| cordic | 已接入平方根数学参考和 Blocking 握手；待补其他运算、非阻塞模式及内部精度审查 |
| floating_point | 已接入绝对值、三种转换、平方根、比较、加减和乘除；待补融合乘加、复位和手动延迟 |
| fir_compiler | 已完成[接口探测](../ip/fir_compiler/interface_probe.md)和全精度边界独立复现，待接入常规卷积参考及参数配置 |
| dds_compiler | 相位配置和状态模型 |
| axis_dwidth_converter | 已接入字节重组、部分字节和侧带检查，待补运行中复位、ACLKEN |
| axis_subset_converter | 已接入位重排、侧带映射和包尾计数，待补稀疏字节、告警接口和运行中复位 |
| axis_broadcaster | 已接入多支路握手与映射，待补稀疏字节和运行中复位 |
| axis_combiner | 已接入独立多输入、拼接和主接口选择，待补稀疏字节、运行中复位 |
| axis_switch | 已接入静态路由、多端口握手和竞争，待补动态路由、请求抑制和授权次序 |
| xlconcat、xlslice、xlconstant | 旧版与 Inline 拼接、截取、常量已分别接入；Inline 向量和归约逻辑也已接入 |
| tmr_voter、tmr_comparator | 已接入离散接口，待补时间冗余、总线和测试注入接口 |
| ecc | 编码位序、纠错规则和受控翻转输入 |

这些是待接入项，不是“无法继续添加”的项目。后续仍按 IP 分目录扩展，
先核对规格与接口，再写参考模型和代表性行为仿真，不加入综合或网表测试。
如果遇到许可证、器件、接口或规格限制，应在对应 IP 记录具体原因。

## 乘加补充探测

编号 `2026-09-14_23-26-57_UTC+0800_a1f5d4be`，三个工程均创建成功，当时尚未功能自检。
`comb_small` 为 8 位无符号乘加；`comb_wide` 为 52 位乘法、105 位加数、非零输出低位；
`pipe_single` 为使用 PCIN 的单 DSP 流水线配置。

依据 [PG192](https://docs.amd.com/v/u/en-US/pg192-multadd)，运算为 C 加减 A*B，
不能把减法写成 A*B-C。A/B 与 C/PCIN 的流水线长度不同，需要分别对齐。
实测组合模式没有 CLK、CE、SCLR 端口；PCIN 模式把 C_C_LATENCY 规范化为 0。
这些接口差别和宽位输出的索引范围，需要在接入时核对，不能沿用普通乘法器假设。
后续已接入，测试方法和限制见[乘加自检](../ip/multiply_adder/selfcheck.md)。

## ECC 和冗余 IP 补充探测

编号 `2026-09-15_00-27-15_UTC+0800_503fd60c`，六个工程都创建成功：
TMR 投票器的比较/旁路和锁步模式，比较器的输入寄存/旁路及 128 位模式，
4 位 Hamming 解码器，128 位 Hsiao 编解码器。
TMR 后续功能检查见[接入记录](tmr_acceptance.md)，不能把创建成功等同于功能通过。

ECC 的 [PG092 解码规则](https://docs.amd.com/r/en-US/pg092-ecc/ECC-Decoder-Operation?contentId=Paps5jK0pntVYFVeQp~zYQ)
说明单错纠正、双错检测以及 `ecc_correct_n` 的旁路行为。
目前读到的文档没有给出这颗 IP 的校验矩阵列序和校验位排列，安装模型是加密的。
因此暂不套用任意一种 Hamming/Hsiao 位序，也不从 DUT 输出拟合参考模型。
下一步需找到公开编码约定，或明确采用编码/解码关系与故障注入检查，并写明共同错误的盲区。
这是当前接入限制，不是宣称 ECC 不能测试。

## 位宽转换补充探测

编号 `2026-09-15_00-59-53_UTC+0800_29fc16ed`，1:4、8:2、3:5 三个工程创建成功。
1:4 输入没有 TKEEP，但启用包尾后输出自动增加 TKEEP；TUSER 宽度随字节数变化。
插件核对这些实际端口，不再假定输入输出位宽相同。
后续自检见[位宽转换接入记录](axis_dwidth_acceptance.md)。

## 子集转换补充探测

编号 `2026-09-15_01-31-25_UTC+0800_34f10332`，三组工程均创建成功：
跨 TDATA/TUSER/TID/TDEST 的映射，以及每 3 拍、每 256 拍生成包尾。
当时尚未功能自检；后续接入结果见[子集转换记录](axis_subset_acceptance.md)。

[PG085 映射规则](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/Extra-Settings)
规定右侧元素放低位，允许切片、二进制常量和跨字段引用。
该模块按拍重映射，不是保留字节序列的位宽转换器，不能直接套用上一项参考模型。
已增加独立映射参考、不同输入输出端口集合，以及按实际握手计数的包尾检查。

## 广播器补充探测

编号 `2026-09-15_02-01-28_UTC+0800_78499f74`，三组工程创建成功，尚未功能自检：

- `full3`：三路 24 位输出，完整侧带，各路数据采用不同映射。
- `split16`：128 位输入分成十六路 8 位输出，16 位 TUSER 也按支路拆分。
- `side4`：无 TDATA，四路 9 位 TUSER 与 TLAST。

实测输出端口按支路打包为向量，低位对应 M00；输入 TLAST 是标量，
输出 TLAST、TVALID、TREADY 都是支路数宽的向量。
不能直接把单输出检查器中的标量信号接到这些端口。

[PG085](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/Overview-of-Features)
规定广播器支持 2 至 16 路输出和数据/用户字段映射。
[延迟说明](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/Performance)
说明各输出都就绪时数据路径为组合逻辑。
后续需要每路独立回压、收包计数和映射参考，允许各路先后握手，
同时防止同一输入被某条支路重复接收。这三次创建不计入已支持的 20 类 IP。
后续已接入行为自检，结果见[广播器记录](axis_broadcaster_acceptance.md)。

## 汇合器补充探测

编号 `2026-09-15_02-26-18_UTC+0800_efef4aef`，三组工程创建成功，尚未功能自检：

- `full3`：三路 24 位输入，完整侧带，主接口选择第 2 路。
- `wide16`：十六路 256 位输入，输出 4096 位，主接口选择第 15 路。
- `side4_errors`：四路无 TDATA 接口，启用侧带和 12 位 `s_cmd_err`。

[PG085 功能说明](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/AXI4-Stream-Combiner?contentId=egtotfYg4MCrFn32jy_dhQ)
规定 TDATA/TSTRB/TKEEP/TUSER 拼接，TLAST/TID/TDEST 取自所选主接口；
所有输入 TVALID 都有效后才允许输出 TVALID。
后续需要独立输入间隔、主接口选择和回压检查，不是简单把广播器的端口方向反过来。

[参数说明](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/Signal-Properties?contentId=gWK1P_lJvAoMKpgPRECHcA)
限制输入字节数乘以通道数不能超过 512。
[端口说明](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/Slave-Interface-Signals)
将 `s_cmd_err` 标为未定义，不能凭实测位序建立错误码参考。
这不妨碍先接入关闭告警接口的功能检查；告警位含义需另找公开规范。

编号 `2026-09-15_02-32-38_UTC+0800_c254dea6` 补测了两项：
16 路各 4096 位 USER 能创建；3 路配置选择主接口 3 会被 Vivado 正确拒绝，
错误号 `IP_Flow 19-3461`，有效编号为 0、1、2。后者不是 IP bug。
后续已接入功能自检，见[汇合器记录](axis_combiner_acceptance.md)。

## 流交换器补充探测

编号 `2026-09-15_02-52-31_UTC+0800_0aa0992c`，三组工程创建成功，尚未功能自检：
一路到三路的目的地址路由、三路到一路的仲裁、三路到三路的交叉连接。
使用静态 TDEST 范围、完整侧带，分别探测译码寄存和输出寄存配置。

[PG085 仲裁规则](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/Data-Flow-Properties)
区分固定优先级、轮询和真轮询，还允许按传输数、包尾或空闲周期释放仲裁。
下一步需独立检查目的端、每路顺序、同目的竞争和回压，不能假设不同输入的全局输出顺序固定。
这三次创建不计入已支持的 22 类 IP。
本机参数枚举为：0 轮询、1 固定优先级、3 真轮询。
即使只有一路，VALID、READY、LAST 和 `s_decode_err` 仍是单元素向量，不能按标量接线。
后续已接入行为自检，见[交换器记录](axis_switch_acceptance.md)。

## AXI-Lite 外设探测

编号 `2026-09-15_03-33-40_UTC+0800_20846133`，3 组 GPIO 和 1 组 Timer 创建成功。
当时只有创建和接口核对，没有功能自检，不计入支持数量。
各自的端口、公开限制和后续检查项见 [GPIO](../ip/axi_gpio/interface_probe.md)
及 [Timer](../ip/axi_timer/interface_probe.md)。
它们都需要寄存器状态模型，不能复用 AXI-Stream 的输入输出透传规则。
GPIO 后续已接入，见[自检范围](../ip/axi_gpio/selfcheck.md)及[寄存器差异](../ip/axi_gpio/register_issue.md)。
Timer 后续补测单计数器、极性和 64 位模式，实际位宽枚举及记录见[接口探测](../ip/axi_timer/interface_probe.md)。
Timer 的非级联计数、捕获和中断已接入自检，见[范围和限制](../ip/axi_timer/selfcheck.md)。
PWM、级联和不停计数的总线访问仍待补充。
INTC 又补测三组配置并完成独立中断观察，见[接口探测](../ip/axi_intc/interface_probe.md)。
ISR 写入的[待确认异常](../ip/axi_intc/isr_write_issue.md)已有最小复现。
后续已接入[普通中断模式自检](../ip/axi_intc/selfcheck.md)，新增 12 组常用配置和 8960 组可选参数，
并隔离出[ME 清零后 IRQ 保持](../ip/axi_intc/master_enable_issue.md)的另一条待确认线索。

## 组合辅助 IP 的边界探测

编号 `2026-09-15_04-24-24_UTC+0800_9e28bec5`，6 组创建成功，尚未功能自检。
[拼接](../ip/xlconcat/interface_probe.md)补测混合位宽和 128 路，
[切片](../ip/xlslice/interface_probe.md)补测 4096 位输入和跨字节位置，
[常量](../ip/xlconstant/interface_probe.md)补测 4096 位输出和超过 64 位的常量值。
这次创建探测未计入支持数量；后续已接入独立参考和行为自检，见[验收记录](utility_acceptance.md)。
旧版创建日志明确提示不再支持并建议迁移，不能仅凭本机仍可运行就忽略这一限制。
替代模块已另做[Inline HDL 创建探测](inline_hdl_probe.md)，后续自检接入见[IP 清单](../ip/catalog.md)。

## 浮点转换探测

编号 `2026-09-15_07-41-35_UTC+0800_7219dc71`，绝对值及三种转换均创建成功。
编号 `2026-09-15_07-43-15_UTC+0800_c05eff1c` 又检查了同格式转换、扩宽、缩窄、
80 位输入以及 64 位有符号/无符号整数输入，均能创建。
同批的零延迟转换被 Catalog 拒绝，有效范围为 1 至 3；这不是 IP bug。

Absolute 是无时钟、无复位的组合接口；不支持的复位和异常标志会被 Catalog 忽略。
三种转换支持的异常标志不同，插件提前拒绝无效组合，并核对实际 XCI。
接口、数值模型及当前限制见[浮点检查](../ip/floating_point/selfcheck.md)。

编号 `2026-09-15_08-08-55_UTC+0800_f96698fa` 补测浮点平方根：
8、16、80 位格式和每 25 周期一次的运算配置都能创建。
该运算只有 INVALID_OP 可选异常位，UNDERFLOW 和 OVERFLOW 会被 Catalog 忽略。
这四组还没有接入数值自检，不计入当前四种已支持运算。

编号 `2026-09-15_08-29-02_UTC+0800_5a448697` 又检查了平方根运算间隔：
4 位精度的 2、5 周期和 64 位精度的 65 周期均能创建。
分别设成 6、66 周期时被 Catalog 拒绝，错误明确给出 1 至 5、1 至 65 的范围。
这与 PG060 的精度位数加一限制一致；无效参数的拒绝不是 bug。
后续功能接入见[平方根记录](floating_point_sqrt_acceptance.md)。

## 浮点比较探测

编号 `2026-09-15_08-47-38_UTC+0800_27b33193`，三组创建成功：
8 位固定小于比较、32 位可编程比较、80 位条件码比较。
本机 `C_Compare_Operation` 枚举列出八种固定比较或条件码模式，另有 Programmable。
前两组的结果有效字段为 1 位，条件码为 4 位，接口仍补齐到字节。
这次只检查创建，不计入已接入的五种浮点运算。
后续需要独立驱动 A、B 输入，可编程模式还需驱动 OPERATION 输入，
不能直接把单输入平方根的驱动当作完整的比较 testbench。
后续已接入独立输入驱动和数值自检，见[比较接入记录](floating_point_compare_acceptance.md)。

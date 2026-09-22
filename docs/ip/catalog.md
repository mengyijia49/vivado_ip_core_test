# IP 清单和运行方法

在仓库根目录先加载一次环境：

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
```

只测某类 IP，或测全部 IP，选一条执行：

```bash
python3 scripts/run_all.py --ip-type divider
python3 scripts/run_all.py --all
```

不带选项运行 6 组快速检查；`--all` 运行 478 组常用配置；
`--config configs/extended_discovery.json` 才读取下表所列的可选大矩阵。
`--ip-type` 可以重复指定；只测某个参数配置可用 `--all --case <case_id>`。
每个被选中的配置只运行一次，不自动重试，不自动增加种子和时序组合。

## 已接入的类型

下面是大矩阵中的不同参数数量，不是已通过测试的数量。

| ip_type | Vivado IP | 参数组数 | 主要检查内容 |
| --- | --- | ---: | --- |
| divider | div_gen | 90 | 商、余数、符号、字节对齐、输出有效时序 |
| multiplier | mult_gen | 2592 | 混合符号、宽度边界、1/2/3/5/8 级流水线 |
| [adder_subtractor](adder_subtractor/selfcheck.md) | c_addsub | 951 | 加减切换、截断、CE、清零优先级 |
| [accumulator](accumulator/selfcheck.md) | c_accum | 504 | 累加溢出、加载、CE、清零 |
| [counter](counter/selfcheck.md) | c_counter_binary | 510 | 上下计数、步长、加载、回绕 |
| [shift_register](shift_register/selfcheck.md) | c_shift_ram | 352 | 延迟深度、顺序、暂停和恢复 |
| [distributed_memory](distributed_memory/selfcheck.md) | dist_mem_gen | 346 | 初始化、写后读、双地址、地址边界 |
| [vector_logic](vector_logic/selfcheck.md) | util_vector_logic | 81 | 按位与、或、异或、取反 |
| [reduced_logic](reduced_logic/selfcheck.md) | util_reduced_logic | 66 | 归约与、归约或、奇偶校验 |
| [axis_register_slice](axis_register_slice/selfcheck.md) | axis_register_slice | 2080 | 四种寄存模式、握手、侧带、回压保持 |
| [axis_data_fifo](axis_data_fifo/selfcheck.md) | axis_data_fifo | 1296 | 同步/异步、普通/包模式、深度、存储类型、顺序 |
| [axis_clock_converter](axis_clock_converter/selfcheck.md) | axis_clock_converter | 2048 | 双时钟、同步级数、侧带、顺序和回压 |
| [block_memory](block_memory/selfcheck.md) | blk_mem_gen | 12320 | 三种 RAM 接口、写模式、字节写、输出寄存和复位 |
| [fifo_generator](fifo_generator/selfcheck.md) | fifo_generator | 181392 | 标准读及 FWFT、首字、顺序、计数、阈值、滞回、满空和复位 |
| [multiply_adder](multiply_adder/selfcheck.md) | xbip_multadd | 11628 | C 加减乘积、混合符号、输出截取、不同路径延迟、CE/清零和 PCIN |
| [complex_multiplier](complex_multiplier/selfcheck.md) | cmpy | 17070 | 复数整数乘法、截断/舍入、有效信号、CE、字节填充和侧带 |
| [tmr_voter](tmr_voter/selfcheck.md) | tmr_voter | 1521 | 逐位多数投票、锁步、旁路、内置比较器和掩码 |
| [tmr_comparator](tmr_comparator/selfcheck.md) | tmr_comparator | 1152 | 副本差异、外部投票错误、掩码、输入寄存和复位 |
| [axis_dwidth_converter](axis_dwidth_converter/selfcheck.md) | axis_dwidth_converter | 5053 | 字节拆分/合并、部分字节、位置字节、空包、侧带和回压 |
| [axis_subset_converter](axis_subset_converter/selfcheck.md) | axis_subset_converter | 16425 | 位重排、字段映射、常量生成、包尾计数、无 TDATA 接口 |
| [axis_broadcaster](axis_broadcaster/selfcheck.md) | axis_broadcaster | 62550 | 多支路独立握手、分段映射、复制、重发与漏发检查 |
| [axis_combiner](axis_combiner/selfcheck.md) | axis_combiner | 37160 | 多路独立到达、拼接、主输入侧带、回压和收发计数 |
| [axis_switch](axis_switch/selfcheck.md) | axis_switch | 93972 | 静态目的路由、多输入竞争、独立回压、按来源和输出分别检查顺序 |
| [axi_gpio](axi_gpio/selfcheck.md) | axi_gpio | 122304 | 单/双通道、输入/输出/双向、默认值、寄存器、中断和 AXI-Lite 握手 |
| [axi_timer](axi_timer/selfcheck.md) | axi_timer | 60 | 单/双计数器、三种位宽、触发与输出极性、暂停、重装载、捕获、脉冲和中断 |
| [axi_intc](axi_intc/selfcheck.md) | axi_intc | 8960 | 四种触发、软硬件中断、锁存、清除、屏蔽、优先级、ILR 和总使能 |
| [xlconcat](xlconcat/selfcheck.md) | xlconcat（旧版） | 15014 | 端口顺序、混合位宽、128 路和位连接错误 |
| [xlslice](xlslice/selfcheck.md) | xlslice（旧版） | 61580 | 截取首尾、单比特、跨字节和未选位干扰 |
| [xlconstant](xlconstant/selfcheck.md) | xlconstant（旧版） | 17161 | 四种常量写法、1 至 4096 位、输出稳定性 |
| [ilconcat](ilconcat/selfcheck.md) | ilconcat（Inline HDL） | 10872 | 1 至 128 路、混合位宽、端口位序和宽输出 |
| [ilslice](ilslice/selfcheck.md) | ilslice（Inline HDL） | 31119 | 第 4095 位、完整输入、跨界截取和未选位干扰 |
| [ilconstant](ilconstant/selfcheck.md) | ilconstant（Inline HDL） | 16861 | 常量解析、全部 1 至 4096 位、未知位和稳定性 |
| [ilvector_logic](ilvector_logic/selfcheck.md) | ilvector_logic（Inline HDL） | 16448 | 与、或、异或、取反、两路输入独立变化和超宽数值 |
| [ilreduced_logic](ilreduced_logic/selfcheck.md) | ilreduced_logic（Inline HDL） | 12336 | 归约与/或/异或、奇偶性、每位单独为一和单独为零 |
| [cordic](cordic/selfcheck.md) | cordic | 685824 | 整数/定点平方根、正余弦、相位范围、舍入、侧带和 Blocking 握手 |
| [floating_point](floating_point/selfcheck.md) | floating_point | 8048248 | 绝对值、三种转换、平方根、比较、加减、乘除、融合乘加/减、倒数、倒数平方根、指数、自然对数、特殊值和侧带 |
| [fir_compiler](fir_compiler/selfcheck.md) | fir_compiler | 96 | 固定整数系数、两种架构、卷积数值、侧带和回压 |
| [dds_compiler](dds_compiler/selfcheck.md) | dds_compiler | 96 | 固定步进和相偏、相位回绕、回压、复位进入与恢复 |
| [processor_system_reset](processor_system_reset/selfcheck.md) | proc_sys_reset | 117 | 脉冲过滤、输入极性、锁定丢失、分阶段释放和输出副本 |
| [clocking_wizard](clocking_wizard/selfcheck.md) | clk_wiz | 48 | MMCM/PLL、输出周期、占空比、锁定、复位解锁和重新锁定 |
| [cic_compiler](cic_compiler/selfcheck.md) | cic_compiler | 256 | 固定倍率抽取/插值、全精度数值、输出数量、回压和输入因果关系 |
| [axi_uartlite](axi_uartlite/selfcheck.md) | axi_uartlite | 84 | 串行回接、字符宽度、校验、收发 FIFO、状态和 AXI-Lite 响应 |
| [convolution](convolution/selfcheck.md) | convolution | 126 | 约束寄存器、多项式奇偶校验、1/2 至 1/7 输出率、回压和输入填充位 |
| [xfft](xfft/selfcheck.md) | xfft | 1344 | 无缩放定点正逆变换、四种实现、输出顺序、帧边界、配置通道和回压 |
| [axi_bram_controller](axi_bram_controller/selfcheck.md) | axi_bram_ctrl | 18 | AXI4-Lite 地址、字节写、保护属性、响应回压和复位后数据保持 |
| [lmb_bram_controller](lmb_bram_controller/selfcheck.md) | lmb_bram_if_cntlr | 68 | LMB 地址译码、保护属性、应答及 BRAM 地址、使能、字节写和数据转发 |
| [axi_timebase_wdt](axi_timebase_wdt/selfcheck.md) | axi_timebase_wdt | 16 | 计数周期、首次和第二次到期、启停、冻结、复位状态及 AXI-Lite 响应 |
| [fit_timer](fit_timer/selfcheck.md) | fit_timer | 96 | 周期中断、单周期脉宽、周期误差、高低有效复位和运行中恢复 |
| [mutex](mutex/selfcheck.md) | mutex | 48 | 多 AXI 端口共享锁、所有者、硬件保护、USER 寄存器和同时竞争 |
| [mailbox](mailbox/selfcheck.md) | mailbox | 100 | 双 AXI-Lite 状态与双向 AXI4-Stream 数据、TLAST 和回压 |
| [util_ff](util_ff/selfcheck.md) | util_ff | 288 | 触发器、锁存器、初值、使能、控制极性和输入反相 |
| [axi_apb_bridge](axi_apb_bridge/selfcheck.md) | axi_apb_bridge | 210 | APB4 地址路由、字节写、保护属性、错误映射、等待和时序保持 |
| [axi_fifo_mm_s](axi_fifo_mm_s/selfcheck.md) | axi_fifo_mm_s | 1620 | AXI-Lite 寄存器、数据包回接、长度、TKEEP、TDEST、回压、复位和中断 |
| [tmr_inject](tmr_inject/selfcheck.md) | tmr_inject | 675 | 目标地址、一次性指令替换、magic、CPU 编号、LMB protection 和透明转发 |
| [axi_sideband_util](axi_sideband_util/selfcheck.md) | axi_sideband_util | 1152 | 五个 AXI4 通道、SMID 旁路、插入、移除、握手和回压 |
| [axi_register_slice](axi_register_slice/selfcheck.md) | axi_register_slice | 16200 | 五个 AXI4 通道、五种寄存模式、停顿保持、吞吐和复位 |
| [axi_lmb_bridge](axi_lmb_bridge/selfcheck.md) | axi_lmb_bridge | 192 | AXI4 burst 到 LMB 的地址、数据、等待、错误、保护和 Pause |
| [axi_clock_converter](axi_clock_converter/selfcheck.md) | axi_clock_converter | 15750 | 五通道异步跨时钟、负载、顺序、回压保持和 USER 字段 |
| [axi_protocol_converter](axi_protocol_converter/selfcheck.md) | axi_protocol_converter | 600 | AXI4 burst 拆成 AXI4-Lite 单拍、地址、响应、ID 和回压 |
| [axi_protocol_checker](axi_protocol_checker/selfcheck.md) | axi_protocol_checker | 10080 | 合法事务、保留 burst、WRAP 长度、传输尺寸和握手稳定性错误 |
| [axi_memory_init](axi_memory_init/selfcheck.md) | axi_memory_init | 46080 | 初始化 burst、地址和数据序列、写响应、ACLKEN、回压及初始化后五通道透传 |
| [ahblite_axi_bridge](ahblite_axi_bridge/selfcheck.md) | ahblite_axi_bridge | 7680 | AHB-Lite 单拍读写、AXI 地址和保护属性、窄传输字节使能、错误响应和回压 |
| [axis_protocol_checker](axis_protocol_checker/selfcheck.md) | axis_protocol_checker | 65536 | AXI4-Stream 复位、回压稳定、有效保持、等待上限、侧带和字节限定规则 |
| [i2s_transmitter](i2s_transmitter/selfcheck.md) | i2s_transmitter | 1200 | AXI-Lite 配置、AXI4-Stream 声道路由、I2S 串行样本、LR 槽宽和时钟分频 |

合计 9667722 组。配置、参考模型、Tcl、测试和专属文档均按 IP 分目录。
本机未能从 Catalog 创建 c_compare 和 c_reg_fd，因此没有将它们列为支持项。
AXI-Lite 外设目前接入 GPIO、Timer、INTC、UART Lite、Timebase Watchdog 和 AXI4-Stream FIFO。
当前常用配置的实测结果见[2026.1 全量运行记录](../experiments/vivado_2026_full_regression.md)。

## 需要更多参数时

先查看计数器的大矩阵，再运行其中选定的配置：

```bash
python3 scripts/run_all.py --config configs/extended_discovery.json --ip-type counter --list-cases
python3 scripts/run_all.py --config configs/extended_discovery.json --ip-type counter --limit 3
```

去掉 `--ip-type` 和 `--limit` 才会运行完整大矩阵。它可能消耗大量时间和磁盘，
不建议拿它检查安装环境。各 IP 的 `extended.json` 可单独调整参数和预算。
同一参数、输入和时序无需重复跑；更换种子或时序是可选实验，不是流程必需步骤。

## 当前限制

实际仿真检查了 478 组常用配置，不能据此宣称 9667722 组大矩阵都可创建或都通过。
大矩阵已检查配置和预算，但 Vivado 的具体限制仍可能使部分配置创建失败。
创建与自检使用 Artix-7 `xc7a35tcsg324-1`；未检查全部大配置是否放得进这颗器件。
测试对象是行为仿真模型，不包括综合后、布局布线后和板级结果。
xlconcat、xlslice、xlconstant 在本机仍能生成，但 Vivado 已提示迁移到 Inline HDL。
ilconcat、ilslice、ilconstant 已按实际 `.bd` 接入自检，分别计入上述数量。
旧版拼接的[128 路异常](xlconcat/port_128_issue.md)已独立复现；ilconcat 的 128 路对照正常，
新版的测试结果单独记录，不把旧版结果移到新版名下。

累加器有 [CE/BYPASS 优先级待确认问题](accumulator/ce_bypass_issue.md)，
对应配置会正常报告失败。它还不是已确认的 IP bug。
复数乘法器另有[手动长延迟异常](complex_multiplier/latency_issue.md)，已用独立 VHDL 复现，
尚待厂商确认；这些失败也不会被自动跳过。
TMR 投票器的[锁步内置比较器展开失败](tmr_voter/lockstep_issue.md)也按原样报告，
不会因为另外一种模式通过就把它排除出测试。
GPIO 的[方向切换和未启用寄存器读回](axi_gpio/register_issue.md)已独立观察到差异，
还需核对手册与版本语义；当前模型不为通过测试而改成实测值。
INTC 的 [ISR 写入](axi_intc/isr_write_issue.md)和[ME 屏蔽](axi_intc/master_enable_issue.md)差异
有不依赖 Python 的独立复现，仍需厂商确认，不将不同参数触发重复计数。
CORDIC 的 Nearest_Even 与精确数学舍入存在[差异](cordic/rounding_review.md)，
需要审查内部精度，而不是把多组触发都算作独立 bug。
浮点转换的[下溢规则](floating_point/underflow_review.md)存在手册正文与注释冲突，
当前参考明确采用正文的舍入后判断，不把该歧义计作实现 bug。
浮点[双精度低延迟乘法](floating_point/multiply_rounding_issue.md)另有远离下溢边界的数值差异，
独立 VHDL 已复现，速度优化对照正常；仍需核对版本、官方记录和厂商结论。
浮点倒数的判定须考虑 PG060 给出的精度范围，不能把数学参考与厂商结果的
任意末位差异直接计作 bug。

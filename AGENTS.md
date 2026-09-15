# Vivado IP 自动测试工程

## 用途和现状

本项目帮助使用者长期测试多种 IP、寻找并复现 bug。使用者计划测试一至两个月，
目标是找到至少 5 个独立 bug；这不是框架已经取得的结果。
PASS 只表示本批测试未发现异常，失败也需要先区分环境、脚本、参考模型和 IP 问题。

当前接入 36 类 IP，各有 Python 参考模型。默认仍为原有 6 组配置、19 个阶段；
`--all` 选择 323 组常用配置，`--ip-type` 可单独运行某类 IP。
大参数矩阵为可选入口，不默认展开多种子和多时序。divider_u16_u8 另有官方 demo。
累加器 CE/BYPASS 存在规范解释与实测差异，按待确认问题保留，不能直接算作 IP bug。
已支持多种子、大预算、系统边界、时序扰动、失败记录、归档和续跑。
失败后扫描全部已有输出，按阶段、字段和流路由有界分组；分组数不是 bug 数。
大矩阵逐项读取并完整校验，配合 --limit 只保留本次要执行的配置，去重使用临时精确索引。
AXI-Stream 后端检查握手、顺序、侧带和回压保持。
位宽转换器另用字节级参考，检查部分字节、位置字节和空包；其他流 IP 仍只发完整字节。
子集转换器按拍检查位重排、跨字段映射和自动包尾，预置映射有独立数值模型。
广播器按支路检查独立握手与映射，允许输出先于上游握手，并检查重复和漏发。
汇合器独立驱动各路输入，检查拼接、主接口侧带和所有输入到齐后的输出。
交换器按来源和输出端口分别比较队列，检查路由和多输入竞争，不假定跨输出完成顺序。
AXI GPIO 使用公共 AXI-Lite 后端，检查寄存器、引脚、中断和响应握手。
AXI Timer 增加固定计数窗口及脉冲观察，检查计数、暂停、重装载、捕获和中断。
Timer 尚未接入 PWM、级联和不停计数时的总线访问，不能把这些功能算作已覆盖。
GPIO 方向切换与未启用寄存器读回存在待确认差异，保留失败和独立 VHDL 记录。
AXI INTC 的 ISR 写入丢失旧位已用独立 VHDL 复现，预编译库与原始 HDL 对照一致。
INTC 已接入公共 AXI-Lite 流水线，另发现 ME 清零后 IRQ 保持异常，已有独立复现。
HIE 启动边界、ILR 非阈值高位编码与部分写仅作观察，不按确定规范评分。
拼接、截取和常量工具通过 Block Design 接入，检查位序、边界和宽常量。
三者为 Vivado 提示迁移的旧版接口；ilconcat、ilslice、ilconstant 替代项已单独接入自检。
Inline HDL 检查并归档实际 .bd 参数、端口和接线，不依赖或伪造独立 XCI。
Inline 向量逻辑和归约逻辑已独立接入，归约另有逐位单独置一/置零输入检查。
逐周期后端的超宽输入 JSON 和覆盖标签使用十六进制，不关闭 Python 整数转换保护。
旧版拼接的 128 路输出异常有独立 VHDL 和直接编译源模型的复现；新版 128 路对照正常。
这些边界参数和失败继续保留，不算作两个独立 bug，也不算作新版 IP 的缺陷。
常量没有输入，报告记录输出观察次数，不把观察次数称为输入事务数。
块存储器和原生 FIFO 按规范标注不确定位，其余有效位及状态标志仍严格比较。
原生 FIFO 支持标准读和 FWFT，后者单独建模首字时序、额外容量和停读保持。
FIFO 另支持数据计数、常量单阈值和滞回阈值，检查截断、更新延迟和复位。
乘加支持组合、流水线和 PCIN，路径延迟单独归档，数值由 Python 独立计算。
复数乘法支持非阻塞整数模式，检查数值、舍入、有效信号和侧带；尚未接入复位。
复数乘法手动长延迟有独立 VHDL 可复现异常，保留失败，尚待厂商确认。
TMR 投票器和比较器已接入离散接口；锁步投票器内置比较器有展开失败，保留证据。
CORDIC 平方根接入数学参考和 Blocking 握手检查；Nearest_Even 有内部精度相关差异，
报告注明参考模型不是厂商位精确模型，不能把这些差异直接计作 IP bug。
Floating-Point 接入绝对值、三种格式转换、平方根、比较、加减、乘法及除法。
加减与乘法使用精确整数参考，复用比较器的独立输入驱动，检查舍入、异常位和侧带。
除法通过整数商余数判断舍入，覆盖除零、无效运算、全部合法运算间隔和独立输入握手。
双精度低延迟乘法的数值异常有固定输入独立 VHDL 复现，速度优化对照正常，尚待确认。
FIR 全精度负系数边界有独立 VHDL 数值差异，两种架构均复现，正系数对照正常。
FIR 尚未接入常规插件；目前使用独立复现命令，不增加已支持 IP 数量。
平方根支持不同运算间隔，使用整数平方与舍入中点比较，不依赖宿主浮点精度。
比较器独立推进 A、B、OPERATION 输入，检查顺序配对、输出补零和侧带拼接。
可编程比较对每组数值轮流执行七种合法操作，不把预留操作码当作有效输入。
下溢参考采用 PG060 正文的舍入后判断规则，另行记录其与注释的冲突。
策略包括 directed_random:1.0、coverage_guided:1.0、exhaustive:1.0。
研究算法和真实 bug 的长期实验尚未完成。

## 工程规则

1. Python 总控，Vivado 只能通过 batch Tcl 调用，不依赖 GUI。
   环境脚本为 /data/Xilinx/2025.2/Vivado/settings64.sh。
   测试范围只限行为仿真（功能仿真）。不得加入综合、实现、综合后网表仿真、
   布局布线后仿真或时序仿真。XSim 编译和展开不是综合。
2. scripts/run_all.py 是兼容入口，代码位于 src/vivado_ip_test/。
   IpBuilder、TestbenchGenerator、SimulationRunner 分别统一负责创建、生成和仿真。
   仿真 Tcl 统一使用 tcl/run_xsim_batch.tcl。
3. 根据 ip_type 选择插件，不根据 case_id 猜测 IP 类型。
   StrategyRegistry 统一选择策略，RunRecorder 统一保存运行记录。
4. 不同 IP 的配置、参数 schema、Tcl、模板、测试和专属文档分目录维护。
   公共配置用 includes 引用单类 IP 配置，不混放各 IP 的参数。
5. 所有运行产物放入 runs/，日志放入 runs/logs/，报告放入 reports/。
   每次运行的目录须含本地日期、时分秒和时区，并避免重名覆盖。
   工程位于 runs/batches/<run_id>/<ip_type>/<case_id>/。
   日志位于 runs/logs/batches/<run_id>/<ip_type>/<case_id>/。
   报告位于 reports/history/<run_id>/，reports/latest 只作符号链接。
6. 不手动修改 runs/ 中的 Vivado 生成文件，不改写历史证据。
   旧产物迁移须核对移动前后的内容。
7. Markdown 使用平实、简短的中文。直接说明做法、结果和限制，
   不堆砌术语，不重复陈述目标；命令、路径和协议名称保留原文。

## 修改后检查

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 -m py_compile scripts/run_all.py
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/run_all.py
```

保留以下状态，不合并或删掉失败分类：

- VIVADO_NOT_FOUND
- CREATE_IP_FAILED
- TIMEOUT
- LOG_NOT_FOUND
- LOG_CHECK_FAILED
- XCI_NOT_FOUND
- BLOCK_DESIGN_NOT_FOUND
- TESTBENCH_GENERATION_FAILED
- SIMULATION_FAILED
- VERIFICATION_FAILED
- PASS

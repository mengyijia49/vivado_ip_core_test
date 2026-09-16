# 锁步内置比较器展开失败

状态：本机和独立 VHDL 均可复现，尚未得到厂商确认。
环境：Ubuntu 22.04、Vivado 2025.2、tmr_voter 1.0 rev 9、Artix-7。
只做行为仿真，错误发生在 XSim 展开阶段，不涉及综合或硬件测试。

## 现象

配置 `C_INTERFACE=0`、`C_TMR=0`、`C_COMPARATOR=1`。
一位无寄存器、17 位有输入寄存器两组均创建成功，但仿真展开失败：

```text
ERROR: [VRFC 10-9565] expression has 4 elements; formal 'compare' expects 1
```

错误指向厂商模型 `tmr_voter_v1_0_vh_rfs.vhd:16720` 的内部端口连接，
不是我们生成的 testbench。此时还没有读入测试向量，也没有产生实际输出。

框架批次：`2026-09-15_00-45-00_UTC+0800_af5554c4`。
配置：`voter_lockstep1`、`voter_lockstep_reg17`。
[首次运行证据](../../../evidence/tmr_voter/lockstep/2026-09-15_00-45-00_UTC+0800_af5554c4/)包含失败摘要、报告、运行清单和日志。

## 独立复现

使用[固定 VHDL](../../../tests/fixtures/ip/tmr_voter/tb_lockstep_probe.vhd)，
直接连接一位 Discrete 输入、输出和四位 Compare，不使用 Python 参考文件。
编号 `2026-09-15_00-46-39_UTC+0800_5eeb6a01`，仍在同一厂商连接处报相同错误。
该 VHDL 的 SHA-256：`ed9f5d3b79859bd9acaf42c7f608312bb4e44865e9de445e070c1ec6878d915b`。
[独立复现证据](../../../evidence/tmr_voter/lockstep/2026-09-15_00-46-39_UTC+0800_5eeb6a01/)包含固定 VHDL、日志和 XCI 参数。

在仓库根目录复现，不覆盖旧文件：

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
stamp="$(date +%Y-%m-%d_%H-%M-%S_UTC%z)_$$"
root="$PWD"
run="$root/runs/framework/lockstep_probe/$stamp/tmr_voter"
logs="$root/runs/logs/framework/lockstep_probe/$stamp/tmr_voter"
mkdir -p "$run/work" "$logs"
cd "$run/work"
vivado -mode batch -source "$root/tcl/ip/tmr_voter/create_ip.tcl" \
  -log "$logs/create.log" -journal "$logs/create.jou" -tclargs "$run" \
  CONFIG.C_INTERFACE 0 CONFIG.C_TMR 0 CONFIG.C_DISCRETE_WIDTH 1 \
  CONFIG.C_COMPARATOR 1 CONFIG.C_INPUT_REGISTER 0 CONFIG.C_VOTER_CHECK 0
vivado -mode batch -source "$root/tcl/run_xsim_batch.tcl" \
  -log "$logs/simulate.log" -journal "$logs/simulate.jou" -tclargs \
  "$run/proj/ip_test.xpr" "$root/tests/fixtures/ip/tmr_voter/tb_lockstep_probe.vhd" \
  tb_lockstep_probe "TMR_LOCKSTEP_PROBE: PASS" "TMR_LOCKSTEP_PROBE: FAIL"
cd "$root"
```

## 当前判断

公开的 [PG268 参数表](https://docs.amd.com/r/en-US/pg268-tmr/User-Parameters)
列出了锁步和内置比较器选项，本机也接受了这组配置。
安装文件中，外层 Compare 连接固定四位；内部比较器在锁步时改为一位。
这与展开器报告相符，优先怀疑 IP 行为模型的内部连接或配置支持问题。
仍需厂商确认组合的支持范围，并在其他版本核对；不能声称硬件也有同样错误。

三路模式的内置比较器和独立 TMR Comparator 已通过代表性功能测试。
当前没有修改厂商文件、关闭错误检查或跳过失败配置。
两个宽度重复触发只记同一待确认问题，不当成两个 bug。

本机更新记录提到 2024.2 修复过锁步参数传播，但没有给出本次端口连接问题的结论。
不能仅凭这条记录认定当前问题已知或未知；下一步还需检查预编译库与源模型两条路径。

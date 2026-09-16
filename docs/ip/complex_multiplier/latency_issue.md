# 手动长延迟异常

状态：本机可复现，尚未得到厂商确认。不能把不同延迟的重复触发算成多个 bug。
环境：Ubuntu 22.04、Vivado 2025.2、cmpy 6.0（模型修订 27）、xc7a35tcsg324-1。
只做行为仿真，没有综合或网表测试。

## 首次发现

批次 `2026-09-15_00-10-17_UTC+0800_10049d3a`，配置 `cmul_long_pipe`。
8 位复数输入，16 位输出分量，DSP Performance、Truncate、Manual 55。
XCI 中 `C_LATENCY=55`，没有被工具改成其他延迟。

第 113 个采样周期，TVALID 和 TUSER 对应 54 个周期以前的输入，期望数值为零，
实际实部为 64。它恰好等于当前输入 `(0+i)*(0-128i)` 截去一位后的结果。
原始输出、逐周期输入、掩码、日志和 failure.json 均保留在该批次中。
这里没有靠普通 ERROR 字符串判断失败，是 testbench 的有效数据比较失败。

## 独立复现

另建不带 CE、复位、TUSER、TLAST 的 IP，使用固定的小 VHDL testbench，
不生成或读取 Python 期望值。所有输入 TVALID 保持为一，通常输入零，
仅在第 80 拍输入实数 `2*1`。从 17 位截到 16 位后，结果应为 1。
55 拍配置下，应在第 134 拍观察到这一个非零结果。

编号 `2026-09-15_00-15-45_UTC+0800_b0ac4b41`。创建成功，仿真日志为：

```text
Failure: CMPY_LATENCY_PROBE: FAIL cycle=80 expected=00000000 actual=00000001
```

日志：`runs/logs/framework/latency_probe/<编号>/complex_multiplier/simulate.log`。
testbench：[tb_latency_55_probe.vhd](../../../tests/fixtures/ip/complex_multiplier/tb_latency_55_probe.vhd)。
可提交的小证据包：[evidence/complex_multiplier/latency](../../../evidence/complex_multiplier/latency/README.md)。

在仓库根目录重现，不覆盖旧目录：

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
stamp="$(date +%Y-%m-%d_%H-%M-%S_UTC%z)_$$"
run="$PWD/runs/framework/latency_probe/$stamp/complex_multiplier"
logs="$PWD/runs/logs/framework/latency_probe/$stamp/complex_multiplier"
mkdir -p "$run/work" "$logs"
root="$PWD"
cd "$run/work"
vivado -mode batch -source "$root/tcl/ip/complex_multiplier/create_ip.tcl" \
  -log "$logs/create.log" -journal "$logs/create.jou" -tclargs "$run" \
  CONFIG.APortWidth 8 CONFIG.BPortWidth 8 CONFIG.OutputWidth 16 \
  CONFIG.MultType Use_Mults CONFIG.OptimizeGoal Performance \
  CONFIG.LatencyConfig Manual CONFIG.MinimumLatency 55 CONFIG.FlowControl NonBlocking \
  CONFIG.RoundMode Truncate CONFIG.ACLKEN false CONFIG.ARESETN false
vivado -mode batch -source "$root/tcl/run_xsim_batch.tcl" \
  -log "$logs/simulate.log" -journal "$logs/simulate.jou" -tclargs \
  "$run/proj/ip_test.xpr" "$root/tests/fixtures/ip/complex_multiplier/tb_latency_55_probe.vhd" \
  tb_latency_55_probe "CMPY_LATENCY_PROBE: PASS" "CMPY_LATENCY_PROBE: FAIL"
cd "$root"
```

也可运行框架内的对照配置：

```bash
python3 scripts/run_all.py --config configs/ip/complex_multiplier/latency_diagnostics.json
```

## 参数对照

批次 `2026-09-15_00-15-23_UTC+0800_2e4701d2`，均为 8 位输入、16 位输出、
无 CE、无复位、无侧带。9 个工程都创建成功，27 个报告阶段完整保存。

| 实现 | 延迟 | 自检结果 |
| --- | --- | --- |
| DSP Performance | Automatic、Manual 1/4/5/8/16 | 全部通过 |
| DSP Performance | Manual 55 | 数值比较失败 |
| DSP Resources | Manual 55 | 通过 |
| LUT | Manual 55 | 通过 |

后续检查仍使用相同数据格式、无 CE、无复位、无侧带，继续缩小延迟边界：

| 批次 | 手动延迟 | 自检结果 |
| --- | --- | --- |
| `2026-09-15_00-26-08_UTC+0800_b47eb073` | 17、31、32、33、40、47、48 | 通过 |
| 同上 | 54 | 数值比较失败 |
| `2026-09-15_00-46-38_UTC+0800_b0717ba6` | 49、50 | 通过 |
| 同上 | 51、52、53 | 数值比较失败 |

因此这组参数在 50 到 51 拍之间出现明确变化，已测的 51–55 拍均失败。
尚未证明其他位宽或输出精度有同一边界。这些重复触发仍只属于同一个待确认问题。
边界配置保存在 `configs/ip/complex_multiplier/latency_boundary.json`，不混入普通回归。

## 当前判断

[PG104 延迟设置](https://docs.amd.com/r/en-US/pg104-cmpy/Core-Latency)说明，
手动设定超过完整流水线的延迟时，输出应增加延迟。
本例的数值和有效信号没有保持对应关系，与这项说明不一致。
独立 testbench 排除了 Python 参考文件、侧带拼接及 CE 随机暂停的影响。

暂按 IP 行为模型或生成配置路径的待确认问题保留，不能断言硬件实现也有相同错误。
后续检查不同手动延迟、LUT/DSP、资源/性能模式，并在其他 Vivado 版本复现、核对厂商记录。
不修改参考模型去接受提前输出，也不跳过失败配置。

本机 `cmpy_v6_0_changelog.txt` 记录过 2022.1 的 Versal 手动延迟修复，
但该记录的器件和条件不同，不能据此认定当前 Artix-7 现象已知或未知。

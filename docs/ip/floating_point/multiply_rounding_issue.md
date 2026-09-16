# 双精度低延迟乘法数值差异

2026-09-15，本机 Vivado 2025.2、Floating-Point 7.1 revision 21、Artix-7 行为仿真出现差异。
当前是一条有独立复现的候选问题，尚无厂商确认，也未证明首次发现或硬件必然受影响。

## 最简单的输入

配置为 Double、Multiply、Low_Latency、Max_Usage、Blocking；自动延迟实际为 13。
无输入 USER/TLAST，结果 READY 恒为 1，启动时正常复位。

| 项目 | 双精度十六进制 | 含义 |
| --- | --- | --- |
| A | `3FEFFFFFFFFFFFFE` | `1 - 2^-52` |
| B | `3FF0000000000001` | `1 + 2^-52` |
| 期望 | `3FF0000000000000` | `1.0` |
| 实测 | `3FE0000000020000` | `0.5 + 2^-36` |

精确乘积是 `1 - 2^-104`，最近偶数舍入应得到 `1.0`。
这远离上溢、下溢和次正规边界，不受[下溢规则歧义](underflow_review.md)影响。
[PG060](https://docs.amd.com/v/u/en-US/pg060-floating-point) 的精度章节规定乘法应正确舍入。
不能仅凭表现断言是 RTL 的哪一处进位或规格化逻辑出错。

## 已有证据

首次由常用配置 `fp_mul64_low` 发现，批次 `2026-09-15_12-54-17_UTC+0800_f23eb1d7`。
失败位置为第 2246 个输出，A 不变，B 为 `3C80000000000001`。
期望 `3C80000000000000`，实测 `3C70000000020000`；宿主双精度与整数参考一致。
失败前实际接收的 2247 组输入与输入文件逐项一致，错误不是配对或输入丢失。
仿真提前结束造成后续 5067 行缺失，这些缺失不另算 bug。

另用固定输入和固定期望值的 VHDL，去掉独立乱序、回压和输入侧带，共观察 16 例。
VHDL 不调用 Python 数值模型，并在边沿采样后才等待计数信号更新。

| 架构 | DSP | 结果 | 复现批次 |
| --- | --- | --- | --- |
| Low_Latency | Max_Usage | 5 个相关数值差异，其余 11 例正常 | `2026-09-15_13-03-11_UTC+0800_ceadf6b0` |
| Speed_Optimized | Max_Usage | 16 例通过 | `2026-09-15_13-03-35_UTC+0800_747a3c9e` |
| Speed_Optimized | No_Usage | 16 例通过 | `2026-09-15_13-04-00_UTC+0800_0e8be551` |

五个差异是同类输入的缩放和符号变化，不算五个独立 bug。异常标志均与期望一致。
13:00 至 13:02 的第一次独立运行也得到相同结果；表中是完善边沿采样后的重跑。
[首次运行](../../../evidence/floating_point/multiply_rounding/2026-09-15_12-54-17_UTC+0800_f23eb1d7/)保留失败摘要、输入、期望、实际输出、报告和日志。
[低延迟独立复现](../../../evidence/floating_point/multiply_rounding/2026-09-15_13-03-11_UTC+0800_ceadf6b0/)和
[速度优化对照](../../../evidence/floating_point/multiply_rounding/2026-09-15_13-03-35_UTC+0800_747a3c9e/)
保留观察摘要、固定 VHDL、日志和 XCI 参数。
[完整证据包](../../../evidence/floating_point/multiply_rounding/README.md)。

厂商随安装提供的 C 数值模型也做了对照：`xip_fpo_mul_d` 对同样 16 例的结果和异常位
全部符合期望。结果见[C 模型对照报告](../../../evidence/floating_point/multiply_rounding/2026-09-15_13-26-17_UTC+0800_209c333a/cmodel_summary.json)。
该接口不区分 Low_Latency 和 Speed_Optimized，只作数值佐证，没有替代框架的独立参考。

## 复现

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type floating_point --case fp_mul64_low
VIVADO_INTEGRATION=1 PYTHONPATH=src:tests python3 -m unittest integration.ip.floating_point.test_multiply_rounding_probe -v
```

独立测试会跑一种低延迟和两种速度优化实现。当前低延迟测试应报告 FAIL，而不是把实测值写成期望。
输入与期望见 `tests/fixtures/ip/floating_point/arithmetic/multiply_rounding_probe.vhd`。

下一步核对其他 Vivado 版本、官方已知问题、更多相邻输入和实现参数。
目前官方站点检索未找到可直接对应的记录，不能据此声称这是新 bug。
本机仅找到 Vivado 2025.2，尚未跨版本验证；附带 change log 也未看到直接对应的说明。
本项目只测行为仿真，不加入综合、网表仿真或板级实验，也不自动提交厂商工单。

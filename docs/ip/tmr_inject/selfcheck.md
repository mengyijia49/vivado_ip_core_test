# TMR Injector 自检

## 怎么运行

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type tmr_inject
```

常用回归有 4 组。扩展矩阵有 675 组，可按需分批运行：

```bash
python3 scripts/run_all.py --config configs/ip/tmr_inject/extended.json --list-cases
python3 scripts/run_all.py --config configs/ip/tmr_inject/extended.json --limit 4
```

## 怎么检查

TMR Injector 位于 MicroBlaze 和指令 BRAM 的 LMB 通路中。控制端先写目标地址和替换指令，
再写带 magic、CPU 编号和使能位的控制字。目标 LMB 地址命中后，IP 把 BRAM 返回的数据
替换为指定指令。一次注入完成后必须重新使能。

Python 模型独立保存目标地址、替换指令、控制写流水线和使能状态。定向测试检查正确和
错误的 magic、CPU 编号、目标地址及地址低两位，还检查重新使能和复位。普通访问必须原样
转发地址、写数据、读写选通、字节选通、ready、wait、UE 和 CE。

启用 LMB protection 时，测试四种保护属性。禁止的控制写必须报告 UE，且不能改变注入
状态。允许的写仍需完成一次注入。报告记录实际注入、无效使能和被拒绝写入的次数。

## 参数

- `base_address`：控制寄存器的 32 位基地址，必须按地址窗口对齐。
- `address_size`：控制寄存器解码窗口，当前测试 2048、4096 和 65536 字节。
- `magic`：使能控制字低 8 位必须匹配的值。
- `cpu_id`：待注入的 CPU 编号，可取 1、2、3。
- `protection`、`protection_mask`：是否启用 LMB protection 及允许的读写属性。

## 当前范围

当前按公开 GUI 约束测试 32 位 Standard LMB。没有接入隐藏的 64 位组合、Frequency LMB
协议、MicroBlaze 系统级执行结果或 TMR Manager。自检只确认 Injector 的端口和状态行为，
不能替代完整 TMR 系统测试。

2026.1 全量运行中的 4 组配置、12 个阶段全部通过，
见[运行记录](../../experiments/vivado_2026_full_regression.md)。

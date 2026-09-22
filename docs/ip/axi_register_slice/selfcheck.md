# AXI Register Slice 自检

## 运行方法

```bash
python3 scripts/run_all.py --ip-type axi_register_slice
python3 scripts/run_all.py --config configs/ip/axi_register_slice/extended.json --list-cases
python3 scripts/run_all.py --config configs/ip/axi_register_slice/extended.json --limit 5
```

常用回归有 5 组，分别检查 Bypass、Full、Forward、Reverse 和 Light。大矩阵有
16200 组参数，组合 32 至 1024 位数据、不同 ID 和 USER 位宽，以及请求、响应通道的
不同寄存模式。

## 检查内容

自检覆盖 AW、W、B、AR、R 五个 AXI4 通道。Python 模型分别保存每个通道的有效位、
负载和停顿状态，再逐拍计算两侧的 VALID、READY 和负载。状态转换按 Vivado 安装包中
公开的寄存器切片 RTL 编写，不使用仿真输出反推期望值。

定向输入会逐个检查五个通道的接收、停顿、保持和排空，也会同时驱动多个通道，并在
运行中再次复位。随机输入补充端口边界和不同回压组合。VALID 为 0 时只忽略对应负载，
VALID 和 READY 每拍都比较。

2026.1 全量运行中的 5 组配置、15 个阶段全部通过，
见[运行记录](../../experiments/vivado_2026_full_regression.md)。
这只说明这些输入没有发现差异，不代表全部大矩阵已经运行，也不代表 IP 没有 bug。

## 当前限制

当前只接入单时钟、读写完整的 AXI4。还没有接入 AXI3、AXI4-Lite、只读、只写、Inputs、
SI_REG、MI_REG、SLR Crossing、TDM 和自动流水线模式。随机部分按单拍端口边界生成，
合法连续事务主要由定向序列提供，因此不能把随机拍数当作完整 AXI 事务数。

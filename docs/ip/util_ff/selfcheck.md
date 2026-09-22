# Util FF 自检

`util_ff` 把一组相同类型的触发器或锁存器封装成可配置 IP。当前支持四种触发器
FDRE、FDCE、FDSE、FDPE，以及两种锁存器 LDCE、LDPE。

## 检查方法

Python 模型保存当前 Q 值。testbench 先检查配置的初值，再依次检查装载、使能关闭时保持、
清零或置位，以及控制释放后重新装载。触发器在时钟沿后比较，锁存器在门控稳定后比较。
低有效异步控制脚在仿真开始时先置为非激活电平，避免正式输入前改写初值。

常用配置覆盖六种类型、8 至 32 位、控制高低有效、触发器数据反相和锁存器门控反相。
运行命令：

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type util_ff
```

可选大矩阵有 288 组，覆盖 8、16、32、64、256、1024 位，两种初值和各种有效极性：

```bash
python3 scripts/run_all.py --config configs/ip/util_ff/extended.json --limit 6
```

## 当前限制

当前固定时钟不反相、`C_FF_LEVELS=1`，没有检查多级结构、亚稳态、建立保持时间或窄脉冲。
这些属于后续行为场景或硬件时序问题，不能由本轮通过结果代替。

2026.1 全量运行中的 6 组配置、18 个阶段全部通过，
见[运行记录](../../experiments/vivado_2026_full_regression.md)。

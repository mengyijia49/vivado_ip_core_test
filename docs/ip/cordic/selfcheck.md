# CORDIC 自检

`cordic` 对应 `cordic:6.0`。目前接入平方根和正余弦，只做行为仿真。

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type cordic
python3 scripts/run_all.py --config configs/ip/cordic/extended.json --limit 3
```

第一条运行 17 组常用配置。原有平方根 Nearest_Even 配置会保留已知差异，因此整批可能返回非零。
第二条只选大矩阵的前 3 组。CORDIC 大矩阵有 685824 组，不默认全跑：

- 平方根 661248 组，配置在 `matrices/square_root/`。
- 正余弦 24576 组，配置在 `matrices/sin_cos/`。

## 平方根

Python 使用 `math.isqrt` 和整数平方比较，不用宿主浮点数计算期望值。
定向输入覆盖平方数、舍入中点、零、最大值及输入填充位。
整数和无符号定点格式、四种舍入、8 至 48 位输入输出均有配置。

PG105 规定输出结果字段向字节边界做符号扩展。即使平方根数值无符号，
补齐位也不能一律按零处理。数值、补齐位、TLAST 和 TUSER 全部比较。

## 正余弦

输入使用 `s_axis_phase`，支持 Radians 和 Scaled_Radians。
输出 `m_axis_dout_tdata` 的低字段是余弦，高字段是正弦，两个字段分别做符号扩展。
Python 用高精度十进制泰勒级数计算理想正弦和余弦，并在两档精度下确认结果稳定。

开启粗旋转时只生成 -Pi 到 Pi 的输入；关闭时只生成 -Pi/4 到 Pi/4。
超出手册范围的值不会进入数值评分。定向输入覆盖零、范围端点、象限边界及相邻编码，
随机输入也会映射到合法范围。

CORDIC 的自动内部精度不保证与理想数学值逐位相同。在线 testbench 和 Python 复核都按
有符号字段计算距离，正弦和余弦各允许 2 LSB；TLAST 和 TUSER 仍须完全一致。
2 LSB 是当前独立参考的工程判定界限，不是厂商位精确模型。超过界限后仍需先核对
迭代次数、内部精度和手册规定，不能直接宣布为 IP bug。

## 接口检查

两种功能都使用 Blocking 模式、输入和输出 TREADY，以及启动时同步复位。
公共 AXI-Stream 驱动会保持未接收的输入，扰动输出 READY，并检查顺序、数量、
未知位和输出停顿期间的稳定性。Python 还会核对实际接收输入和实际输出文件。
参考模型不写死流水延迟。

本机 Catalog 在平方根模式下会忽略 Word_Serial，当前插件只接入 Parallel。
尚未接入 Rotate、Translate、Sinh/Cosh、ArcTan、ArcTanh、NonBlocking、ACLKEN、
运行中复位和手动迭代/精度。

平方根 Nearest_Even 的已有差异见[舍入审查](rounding_review.md)。
实际运行记录见[2026.1 全量运行记录](../../experiments/vivado_2026_full_regression.md)。

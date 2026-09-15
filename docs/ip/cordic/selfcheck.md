# CORDIC 平方根检查

`cordic` 对应 `cordic:6.0`。目前只接入 Square_Root，只做行为仿真。

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type cordic
python3 scripts/run_all.py --config configs/ip/cordic/extended.json --limit 3
```

第一条运行 11 组常用配置，包含已知的数学舍入差异，因此当前整批会返回非零。
第二条只选大矩阵的前 3 组；大矩阵共 661248 组，不默认全跑。
它包含全部 8 至 48 位输入、定点输出 8 至 48 位、四种舍入、三种流水选择、
两种优化目标、可选 TLAST 和八种 TUSER 设置。整数输出宽度由输入宽度决定。
配置分别放在 `matrices/square_root/integer.json` 和 `fractional/`。

## 方法

Python 使用 `math.isqrt` 和整数平方比较，不用浮点近似生成期望值。
整数模式直接计算平方根；定点模式的输入、输出都保留一位整数位。
定向序列覆盖平方数前后、舍入中点前后、零、最大值，以及输入填充位的变化。
这不是整个长数据序列的穷举。

根据 [PG105 第 15 页](https://docs.amd.com/api/khub/documents/NHMqdvRJIfgF8hdbQmLFuA/content)，
输入补齐位忽略，输出结果字段向字节边界做符号扩展。
即使平方根数值无符号，也不能把输出补齐位一律当作零。
数值、补齐位和侧带全部比较，没有给输出加掩码。

使用 Blocking 模式、输入和输出 TREADY、启动时同步复位。
公共 AXI-Stream 驱动保持未被接收的输入，独立扰动输出 READY，
检查输出停顿期间的稳定性、顺序、数量、未知位及 TLAST/TUSER。
Python 再核对实际接收的输入文件和输出文件。
不预设固定流水延迟，也不把延迟实测值写进参考模型。

## 参考模型的边界

当前比较的是精确数学值舍入后的结果，不宣称与厂商有限精度算法逐位等价。
报告的 `reference_contract` 保存这个区别。Nearest_Even 已出现[舍入差异](rounding_review.md)，
需要先检查内部精度规定，不能仅凭 FAIL 认定厂商 bug。
厂商 C 模型只用于独立诊断，不参与自动流程中的期望值生成。

本机 Catalog 在平方根模式下会忽略 Word_Serial，插件提前拒绝该参数。
尚未接入其他 CORDIC 运算、非阻塞接口、运行中复位、ACLKEN 及手动迭代/精度。
所有设置、模型参数和实际端口都会与生成后的 XCI 核对。

本轮实际运行和检查结果见[接入记录](../../experiments/cordic_acceptance.md)。

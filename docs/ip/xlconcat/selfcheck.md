# 拼接工具自检

对象是 `xlconcat:2.1`，不是 Inline HDL 的 `ilconcat`。
Vivado 2026.1 仍能创建该 IP，但日志提示迁移到 Inline HDL。

`input_widths` 按 `In0`、`In1` 等端口顺序列出宽度。
端口数为 1 至 128，每路 1 至 4096 位；`dout` 宽度等于各路之和。
没有时钟、复位或握手，1 位端口仍是向量。
参考模型从低位开始放置 `In0`，再放 `In1` 等端口，用整数乘法和加法计算结果。

测试先用一组位模式让各物理位在多次采样中呈现不同值，再补边界值和随机输入。
这样可以检查端口接反、相邻位错接、遗漏某路和卡住的位，不必对每一位都保存
一整套超宽独热输入。采样发生在输入稳定后，不检查毛刺或传播延迟。

```bash
python3 scripts/run_all.py --ip-type xlconcat
python3 scripts/run_all.py --config configs/ip/xlconcat/extended.json --list-cases
```

常用回归有 6 组。大矩阵有 15014 组：所有端口数的统一位宽、两路及三路混合宽度，
以及多路接口中只有某一路变宽的配置。它们不是已全部仿真通过的配置。
大于 8 位的输入空间只取部分样本；最大配置的输出有 524288 位，会产生较大文件。
128 路的两组回归已发现[非零输入输出仍为零的问题](port_128_issue.md)，
独立 VHDL 与直接编译源模型均可复现。参数和失败继续保留，不自动改成通过。

创建采用 batch Tcl 的 Block Design 流程，符合 [PB041 的 IP Integrator 使用范围](https://docs.amd.com/v/u/en-US/pb041-xilinx-com-ip-xlconcat)。
生成前后分别核对配置和 XCI，不读取 IP 输出来修正参考值。
验证结果见[2026.1 全量运行记录](../../experiments/vivado_2026_full_regression.md)。

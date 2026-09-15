# FIR 全精度输出的符号边界异常

2026-09-15，Vivado 2025.2、FIR Compiler 7.2 revision 26、Artix-7 行为仿真。
目前是一条可独立复现的候选问题，尚无厂商确认，不代表首次发现或硬件已证实受影响。

## 现象

8 位有符号输入、4 位整数系数、Single_Rate、Full_Precision，单通道、单数据路径。
启动时复位并清空数据历史，不重载系数。两种架构都有相同差异：

| 系数 | 触发条件 | 数学结果 | XSim 实测 | 自动结果位宽 |
| --- | --- | --- | --- | --- |
| `[-8, 0, 0]` | 当前输入为 `-128` | `1024` | `-1024` | 11 |
| `[-1, -1, -2]` | 连续三个输入均为 `-128` | `512` | `-512` | 10 |
| `[1, 1, 2]` | 相同输入序列，正系数对照 | 全部符合 | 全部符合 | 10 |

第一组仅需计算 `(-128) * (-8)`。第二组为 `128 + 128 + 256`。
11 位有符号数的最大值是 1023，10 位是 511；这两个正结果各需要再多一位。
接口虽然补齐到 16 位，XSim 输出已经按偏小的结果位宽做了符号扩展。
不能再把数学参考截成同样的位宽，否则会把这条线索掩盖掉。

## 为什么需要排查

[PG149 的 Filter Types](https://docs.amd.com/r/en-US/pg149-fir-compiler/Filter-Types)
说明内部数据路径采用足够的精度来避免溢出。
[位宽章节](https://docs.amd.com/r/en-US/pg149-fir-compiler/Output-Width-and-Bit-Growth)
按固定系数的绝对值之和计算位增长。
2022-10-26 版 [PG149](https://www.xilinx.com/support/documents/ip_documentation/fir_compiler/v7_2/pg149-fir-compiler.pdf)
第 5、64、65 页也给出这些规则，并说明 Full_Precision 不削减输出位宽。
当前网页版日期为 2026-07-22，晚于本机安装版本，不能用它替代版本核对。

当前推测是位宽估算没有完整处理补码正负范围不对称的边界。
两组系数及两种架构暂归同一问题，不能按失败次数增加 bug 数量。
还需要厂商澄清这一输入是否受额外限制，以及问题属于生成参数、行为模型还是文档。

## 独立证据

`tests/fixtures/ip/fir_compiler/full_precision_probe.vhd` 写死 16 个输入及三组期望，
不调用 Python 数值参考。它逐笔等待输入握手，只在输出握手时比较结果，
同时检查 USER、TLAST、回压保持、未知值、多发、过早输出及超时。
TLAST 每四笔一次，不重置卷积历史。负系数测试继续收完 16 笔，再汇总数值错误。

| 架构 | 系数 | 结果 | 批次 |
| --- | --- | --- | --- |
| Systolic | `[-1,-1,-2]` | 第 4 笔差异 | `2026-09-15_14-51-46_UTC+0800_78b0eb6a` |
| Transpose | `[-1,-1,-2]` | 第 4 笔差异 | `2026-09-15_14-52-06_UTC+0800_ea810713` |
| Systolic | `[-8,0,0]` | 第 2 至 4 笔差异 | `2026-09-15_14-52-27_UTC+0800_52bc0e17` |
| Transpose | `[-8,0,0]` | 第 2 至 4 笔差异 | `2026-09-15_14-52-48_UTC+0800_1da68cae` |
| Systolic | `[1,1,2]` | 16 笔通过 | `2026-09-15_14-53-10_UTC+0800_c9615d60` |
| Transpose | `[1,1,2]` | 16 笔通过 | `2026-09-15_14-53-31_UTC+0800_1d07609e` |

更早的 14:45、14:46 两次 Systolic 测试也复现同样差异。
14:57 至 14:59 使用补齐日志哈希的最终程序重跑六项，仍为四项数值失败、两项正常对照通过。
报告位于 `reports/framework/fir_full_precision_probe/<批次>/summary.json`；
工程和源码位于 `runs/framework/fir_full_precision_probe/<批次>/fir_compiler/`，
日志位于 `runs/logs/framework/fir_full_precision_probe/<批次>/fir_compiler/`。

厂商 C 模型 7.2.1 也跑了三组系数，每组比较自动位宽和足够位宽，共 96 个结果，均符合固定期望。
首份成功记录为 `reports/framework/fir_cmodel_probe/2026-09-15_14-55-59_UTC+0800_3afbed91/summary.json`。
但自动模式仍报告 11/10 位，同时用 `double` 返回 1024/512；它没有提供对应的 AXI 位向量。
所以这份对照只支持数学结果，不证明 C 模型的位宽声明正确，也不检查架构和握手。
手动增大 C 模型的累加器位宽不是已经验证的 Vivado IP 修复办法。

## 重跑

在仓库根目录运行：

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
VIVADO_INTEGRATION=1 PYTHONPATH=src:tests python3 -m unittest integration.ip.fir_compiler.test_full_precision_probe -v
VIVADO_INTEGRATION=1 PYTHONPATH=src:tests python3 -m unittest integration.ip.fir_compiler.test_cmodel_probe -v
```

第一条测试命令当前应有 4 项 FAIL、2 项 PASS；第二条应通过。
FAIL 是严格数值比较的结果，没有改成 expectedFailure，也没有把错误期望写入测试。
C 对照需要 gcc 和本机安装附带的 C 模型压缩包；厂商库只解包到带时间戳的 runs 目录。
FIR 尚未接入 `--ip-type` 常规流水线，目前使用以上专用命令。

2026-09-15 检查本机 change log 和官方站点，尚未找到直接对应的修复说明。
官方主记录 54502 页面未返回正文，不能声称已排除所有已知问题。
后续补相邻系数、数据位宽、更多器件和其他 Vivado 版本；仍只做行为仿真。

## 收尾检查

本轮按使用者要求停止扩充，不升级 Vivado，不继续接入 FIR 常规插件。
上面列出的后续排查只记录剩余疑点，不自动执行。

`py_compile` 通过；完整 unittest 共 663 项，其中 477 项通过、186 项真实集成测试默认跳过。
检查包含 9472890 组可选参数的合法性和去重，耗时约 1246 秒，峰值内存约 12.24 GiB。
记录：`reports/framework/fir_probe_validation/2026-09-15_15-00-51_UTC+0800_e38d91c5/summary.json`。
FIR 的四项真实数值失败由专用集成命令单独记录，不包含在上述通过数量中。

默认批次 `2026-09-15_15-21-37_UTC+0800_4dfd8ebf` 的六组 IP、19 个阶段全通过。
18 份输入、期望和实际输出与上一批一致，292 份源码、530 份归档文件哈希核对通过。
完整检查后源码、测试和配置没有变化；收尾只补文档。
记录：`reports/framework/fir_closeout_audit/2026-09-15_15-33-13_UTC+0800_9144c772/summary.json`。

14 次 VHDL 复现及两次 C 对照的已有哈希核对通过；生成的系数文件与请求值一致。
记录：`reports/framework/fir_probe_audit/2026-09-15_15-02-31_UTC+0800_8ce4942b/summary.json`。
没有修改历史 Vivado 生成文件，没有把临时配置错误和编译告警计作 IP bug。

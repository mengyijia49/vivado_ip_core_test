# Multiplier 数值自检

当前使用 `mult_gen:12.0` 并行乘法器、完整精度输出，不启用使能和同步清零。
端口只有输入 `CLK`、`A`、`B` 和输出 `P`，没有 tvalid/tready。

## 默认配置

| 配置 | A | B | 输出位宽 | XCI 时延 |
| --- | --- | --- | ---: | ---: |
| `multiplier_u8_u8` | 8 位无符号 | 8 位无符号 | 16 | 2 |
| `multiplier_s16_u8` | 16 位有符号 | 8 位无符号 | 24 | 3 |
| `multiplier_u2_u2_exhaustive` | 2 位无符号 | 2 位无符号 | 4 | 1 |

## 怎么比较

Python 按各输入的符号类型计算 `product = A * B`，
再按输出位宽编码为补码。输入包括边界和随机值；
2 位无符号配置穷举全部 16 种输入对。

testbench 在采样上升沿前稳定输入，按 XCI 的 `C_LATENCY` 等待输出后逐项比较。
输出位宽取 `C_OUT_HIGH - C_OUT_LOW + 1`，完整精度模式要求 `C_OUT_LOW=0`。
时延来自实际 XCI，不在模板中固定为某组配置的数值。

该配置没有使能，探索模式中的“间隔”实际是保持上一对输入。
保持期间每周期仍有一次计算，全部展开到期望文件中并检查，
不能把这些重复输入计为新增数值覆盖。

通过标记是 `MULTIPLIER_SELF_CHECK_STATUS: PASS`，
数值差异、文件提前结束或超时产生 FAIL 标记。
仿真后 Python 再比较期望和实际文件，使用的仍是同一份期望值。

## 文件和限制

每批文件位于 `runs/batches/<run_id>/multiplier/<case_id>/`：

```text
manifest.json
tb/tb_multiplier_selfcheck.vhd
vectors/input_vectors.txt
vectors/expected_output.txt
vectors/vectors.json
vectors/schedule.json
outputs/actual_output.txt
outputs/failure.json          失败时生成
```

当前配置不提供官方 demo，直接使用框架自检。
尚不支持截位、舍入、常量乘法、使能和同步清零测试。
参数约束见[配置说明](configuration.md)。

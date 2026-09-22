# 浮点比较器检查

定向 USER 的全宽变化和旧版覆盖缺口见[修正说明](user_patterns.md)。

比较器是 `floating_point` 插件的一个子模块，配置、参考、输入生成和模板均放在各自的
`compare/` 下。仍从公共 TestbenchGenerator 和 SimulationRunner 调用，不增加零散入口。

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --config configs/ip/floating_point/regression/compare.json
python3 scripts/run_all.py --ip-type floating_point --case fp_compare80_programmable_or
```

第一条运行 17 组比较配置；第二条只运行一组。全部浮点功能使用 `--ip-type floating_point`。
固定模式矩阵为 `matrices/compare/fixed.json`，可编程模式为 `matrices/compare/programmable.json`。
它们相对于 `configs/ip/floating_point/`，合计 1191960 组，不默认全部仿真。
矩阵按指数和精度拆分，单个叶文件不超过 19656 组；长测可逐文件运行并保存报告。

## 参数和数值

`operation` 固定为 Compare，A/B 使用相同的 `input_exponent`、`input_fraction`。
格式总宽为两者之和，接口向上补齐到整字节，输入补齐位不参与数值比较。
`compare_operation` 选择七种布尔比较、Condition_Code 或 Programmable。
比较没有输出浮点格式参数，也不启用数值运算的异常标志。

参考只用整数比较符号、指数和尾数，不调用厂商模型或宿主浮点比较。
次正规输入按带符号的零处理；正负零相等，NaN 走无序比较规则。
结果总线为 8 位，布尔结果只有最低位有效，条件码使用低四位，其余位必须为零。
规则依据 [PG060 的比较编码和输出通道说明](https://docs.amd.com/v/u/en-US/pg060-floating-point)。

`a_user_width`、`b_user_width`、`operation_user_width` 分别为 0 至 256 位，0 表示不启用。
输出用户字段从低到高拼接 A、B、OPERATION，不在字段之间补齐。
`has_a_last`、`has_b_last`、`has_operation_last` 选择包尾输入；`last_mode` 可选透传某路、Or、And。
不启用包尾时使用 None；固定比较不能启用 OPERATION 的侧带。

## 输入与检查

策略先选 A/B 数值及用户字段，随后增加特殊值交叉、相等值、相邻值和补齐位变化。
Programmable 对每组输入依次执行全部七种合法操作，变化操作码的高两位；不发送预留编码。
所以 `case_budget` 不是最终的输出次数，具体数量记录在报告中。
8 位常用配置穷举全部 65536 对数值，宽格式用定向边界加随机输入。

各路有独立文件游标和等待间隔。某一路握手后可以继续发下一项，不等待其他路到齐。
每路保持 VALID 和数据直到 READY，并记录实际接收的完整字段。
输出按各路的第 n 次接收配对检查，另检查未知值、漏发、多发、错序和回压期间的保持。
初始复位持续 200 ns，末次输出后继续观察 128 周期。

目前只接入 Blocking、自动延迟、每周期可接受一次的配置。
不检查固定延迟、性能指标、运行中复位、ACLKEN 或 NonBlocking。
所有请求参数和实际接口会与 XCI 核对；通过不代表全部内部状态都覆盖。
2026.1 的实际结果见[全量运行记录](../../experiments/vivado_2026_full_regression.md)。

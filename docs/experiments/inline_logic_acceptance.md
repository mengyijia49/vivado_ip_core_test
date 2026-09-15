# Inline 逻辑接入检查

2026-09-15，Vivado 2025.2。只运行行为仿真，没有综合或网表仿真。
新增 Inline 向量逻辑和归约逻辑，配置、参考模型、Tcl、测试和文档分别放在各自目录。
本轮完成时共 32 类 IP、192 组常用参数、574614 组可选矩阵参数，没有全量运行大矩阵。

## 创建探测

编号 `2026-09-15_05-59-41_UTC+0800_f3b1fac0`，七组创建成功：

- ilvector_logic：1 位取反、1 位与、33 位或、65536 位异或。
- ilreduced_logic：1 位与、33 位或、65536 位异或。

`parameters.json` 保存探测参数和诊断脚本哈希，命令在对应 `create.log` 中。
工程位于 `runs/framework/catalog/<编号>/<模块>/<运算和宽度>/`，日志在对应 `runs/logs/` 下。
实际 `.bd` 确认：取反没有 Op2；归约 Res 是标量，其他数据端口都是向量。
安装包没有给出明确最大位宽，不能把当前 65536 位接入范围写成厂商上限。

## 功能自检

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type ilvector_logic --ip-type ilreduced_logic
```

编号 `2026-09-15_06-04-49_UTC+0800_659c36cc`，19 组配置、57 个阶段全部 PASS。
向量逻辑包含四种运算、单比特、不同字长和 65536 位取反。
归约包含三种运算、奇偶宽度、4096 位与/或，以及 8193 位异或。
8193 位归约实际比较 16673 行，其中包含每一位单独为一、单独为零的输入。
242 份源码和 986 个归档产物的哈希均核对一致。

另运行 `--config configs/ip/ilreduced_logic/extended.json --case ilreduced_logic_xor__width_65536`，
编号 `2026-09-15_06-11-29_UTC+0800_ef51b2db`，三个阶段全部 PASS。
共比较 131363 行，包含全部 65536 位的单一和单零模式。
创建约 4.47 秒，生成约 19.35 秒，仿真阶段约 187.45 秒。
输出哈希为 `4281979328b3f299913feb492f8b00f0210dd8f70cad850673c5a4459e42c1f9`。
242 份源码和 282 个归档产物的哈希均核对一致。

## 检查器测试

```bash
VIVADO_INTEGRATION=1 PYTHONPATH=src:tests python3 -m unittest \
  integration.ip.ilvector_logic.test_failure_detection \
  integration.ip.ilreduced_logic.test_failure_detection -fv
```

9 项真实 XSim 检查全部符合预期，耗时约 139 秒。
正确替身通过；丢高位、错运算、输入移位和未知位被检测到。
这些是人为制造的错误，不计作 AMD IP bug。

## 框架修补

超宽输入此前会在覆盖标签或 JSON 十进制转换处触发 Python 的整数保护。
现改为可还原的十六进制字符串，小数值和仿真的完整二进制文件不变。
单元测试检查了 65536 位数值、失败输入定位和转换保护未被关闭。

完整测试还触发过一个已有竞态：读取 `/proc/<pid>/stat` 时进程刚好被回收，
系统返回 `ProcessLookupError`。进程已经消失，应视为清理成功；测试已补上这一分支。
没有因此修改 Vivado 执行器或弱化“超时后不得留下活进程”的检查。

修复后运行 `python3 -m py_compile scripts/run_all.py` 及完整 unittest：
474 项中 328 项通过，146 项真实工具测试按规则跳过，耗时约 185 秒。

公共后端另复跑 `counter_updown_control` 和 `bram_sp_nochange9`，编号
`2026-09-15_06-15-30_UTC+0800_15397310`，六个阶段全部 PASS。
该批核对了 242 份源码和 320 个归档产物哈希，均一致。
两组的输入、期望、周期及调度文件，连同块存储器掩码，与
`2026-09-15_05-25-34_UTC+0800_5d6e44a9` 的对应文件逐字节一致。

最后运行不带选项的 `python3 scripts/run_all.py`，编号
`2026-09-15_06-16-26_UTC+0800_2cba50f3`，原有六组配置、19 个阶段全部 PASS。

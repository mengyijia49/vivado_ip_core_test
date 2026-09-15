# 128 路拼接异常

2026-09-15，Vivado 2025.2，`xlconcat:2.1` 修订 7。
本机旧版 128 路模型可以生成和展开，但非零输入没有得到正确输出。
这是可复现的问题线索，还没有厂商确认；两组触发配置不能算成两个独立 bug。

## 现象和复现

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type xlconcat --case concat_bits128
```

原始批次为 `2026-09-15_04-59-48_UTC+0800_453f0aae`。
`concat_bits128` 和 `concat_edges128` 的创建、testbench 生成均通过，数值仿真失败。
第一组有 128 个 1 位输入，第二组首尾为 4096 位，其余为 1 位。
输入由全 0 变成全 1 后，期望输出为全 1，实测仍为全 0。

## 独立对照

手写 VHDL 模板不读取向量文件，不调用 Python 参考模型。
先等待 1 us，再检查全 1、持续全 1、最高位、最低位和交替位，最后一次在 10 us。
观察完成标记只表示记录结束，不代表数值通过。

```bash
VIVADO_INTEGRATION=1 PYTHONPATH=src:tests python3 -m unittest \
  integration.ip.xlconcat.test_port_boundary_probe -v
```

| 对照 | 运行编号 | 结果 |
| --- | --- | --- |
| 旧版 127 路 | 2026-09-15_05-09-04_UTC+0800_28080188 | 六次观察均匹配 |
| 旧版 128 路，默认预编译库 | 2026-09-15_05-09-24_UTC+0800_d28d8ad8 | 只有全 0 匹配，其他五次输出仍为 0 |
| 旧版 128 路，直接编译附带源模型 | 2026-09-15_05-11-31_UTC+0800_32ec8e45 | 与预编译库相同 |
| Inline HDL 128 路 | 2026-09-15_05-08-45_UTC+0800_5a21256b | 六次观察均匹配 |

参数、独立 testbench 哈希和逐次观察保存在：
`runs/framework/port_boundary_probe/<编号>/<IP>/n<路数>/observations.json`。
日志在对应 `runs/logs/framework/port_boundary_probe/`。

## 当前判断

Catalog 的 `NUM_PORTS` 明确允许 1 至 128，生成的 XCI 也记录了 128。
Block Design 顶层逐路连接完整，独立 VHDL 已排除公共文本输入和 Python 模型的影响。
安装附带的 `xlconcat_v2_1_vl_rfs.v` 只包含 1 至 127 路的赋值分支，没有 128 路分支；
生成工程中的对应文件与安装文件哈希一致：

```text
81296f139bbf05959172c666e24197d680ee6b14f0b59bb8b920f1cc044bed4c
```

默认仿真链接 `xlconcat_v2_1_7` 预编译库；另建纯源文件仿真工程后仍能复现。
这些证据指向旧版模型缺少边界处理，不是 XSim 整体损坏，也不是数值参考需要改成 0。
原始失败与 128 路参数继续保留，不把参数上限缩到 127 来取得 PASS。

需要注意：Vivado 已明确提示旧版从 2025.2 起不再支持并建议使用 Inline HDL。
替代接口见 [UG835](https://docs.amd.com/r/2024.2-English/ug835-vivado-tcl-commands/create_bd_cell)。
新版 128 路对照正常；还需核查历史版本、官方问题记录和维护范围，
才能判断这是否可作为新的缺陷报告或论文结果。不能把它包装成新版 IP 的未修复 bug。

# AXI GPIO 接入检查

2026-09-15，Vivado 2025.2，`axi_gpio:2.0` 修订 37，Artix-7。
仅创建模型、生成 testbench 和行为仿真，没有运行综合或网表仿真。

## 常用配置

编号 `2026-09-15_04-23-12_UTC+0800_645984dd`，12 组全部完成 3 个阶段。
创建和 testbench 生成均通过；4 组仿真通过，8 组因数值差异报告 SIMULATION_FAILED。

| 配置 | 操作数 | 差异行数 |
| --- | ---: | ---: |
| gpio_bidir1 | 2087 | 192 |
| gpio_output32 | 1558 | 51 |
| gpio_input32_irq | 3391 | 8 |
| gpio_dual_bidir_bidir | 5312 | 1567 |
| gpio_dual_bidir_in | 4791 | 530 |
| gpio_dual_bidir_out | 4689 | 534 |
| gpio_dual_in_bidir | 4866 | 1298 |
| gpio_dual_in_in | 4345 | 0 |
| gpio_dual_in_out | 4243 | 0 |
| gpio_dual_out_bidir | 4761 | 1367 |
| gpio_dual_out_in | 4240 | 0 |
| gpio_dual_out_out | 4138 | 0 |

所有配置的实际请求文件与计划输入一致，响应握手检查没有报错。
203 份源码与当前版本一致，740 份归档文件哈希核对通过。
差异集中在方向切换与未启用寄存器读回，详见[独立复现](../ip/axi_gpio/register_issue.md)。
一个状态差异可能影响后续很多行，不能把这些行数当成 bug 数量。

## 额外边界

编号 `2026-09-15_04-27-50_UTC+0800_e412d648`，两组、6 个阶段全部通过：

- 两通道均为 32 位输出，通道 1 默认值为 0xFFFFFFFF，有中断，7730 次操作。
- 通道 1 为 32 位输入、通道 2 为 32 位输出，默认值为 0x80000000，有中断，7835 次操作。

每组使用 512 个数值样本，再展开定向和顺序访问。
203 份源码、292 份归档文件哈希核对通过。

## 检查器能否报错

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
VIVADO_INTEGRATION=1 PYTHONPATH=src:tests python3 -m unittest integration.ip.axi_gpio.test_failure_detection -v
```

23 项真实 XSim 检查全部通过，耗时约 360 秒：1 个正常对照、22 个故障对照。
正常对照让 AW 和 W 分别在不同周期握手，检查器正确接受，收到了 6 个写响应、5 个读响应。
期望值手工列出，没有调用 GPIO 参考模型或操作生成器。

故障覆盖数据损坏、丢响应、重复响应、回压期间数据/响应码变化、VALID 提前撤销、
未知 VALID/READY/读数据、错误响应码、复位失效、错误地使用 WSTRB、中断丢失，
以及未收到请求或请求尚未完成就响应。
这证明检查器能捕获这些预置故障，不是发现了 22 个真实 IP bug。

本轮目录编号从 `2026-09-15_04-23-11_UTC+0800_e0918501` 到
`2026-09-15_04-28-56_UTC+0800_aa0538bd`，位于
`runs/framework/failure_detection/<编号>/axi_gpio/` 及对应日志目录。
独立 GPIO 短程序另有一次真实运行，记录在[寄存器问题](../ip/axi_gpio/register_issue.md)中。

## 配置和代码检查

GPIO 新增 122304 组参数，整体为 24 类 IP、132 组常用配置、397 个阶段。
大矩阵合计 393223 组，全部配置、预算与重复组合检查通过，没有全跑 Vivado。
`py_compile` 通过。366 项 Python 检查中，268 项通过，98 项真实工具测试默认跳过；
上面的 23 项故障对照已另行显式执行。

接入中修正了输出读回版本、固定方向 TRI 初值、寄存器有效位、采样等待，
还修正了正常对照测试中把 `aw=11` 误当成 `w=11` 的文本匹配错误。
这些都是框架或测试代码问题，旧日志保留，不计为 IP 缺陷。

默认回归编号 `2026-09-15_04-28-52_UTC+0800_1e637e51`，原有 6 组配置、19 个阶段全部 PASS。
状态为 completed、NO_FAILURE_OBSERVED，203 份当前源码和 441 份归档文件哈希一致。

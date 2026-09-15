# GPIO 寄存器差异记录

2026-09-15，Vivado 2025.2，`axi_gpio:2.0` 修订 37，行为仿真。
以下结果均未经过厂商确认，不计入已确认 IP bug。

## 独立复现

不调用 Python 参考模型，也不读取框架生成的输入文件。
使用[短 VHDL 程序](../../../tests/fixtures/ip/axi_gpio/tb_register_probe.vhd)，
配置为单通道 8 位双向、关闭中断、初始 DATA=0、TRI=0xFF。

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
VIVADO_INTEGRATION=1 PYTHONPATH=src:tests python3 -m unittest integration.ip.axi_gpio.test_register_probe -v
```

本次编号 `2026-09-15_04-14-59_UTC+0800_a1d65faf`。
`runs/framework/register_probe/<编号>/axi_gpio/observations.json` 保存参数、观测值和 VHDL 哈希。
完整命令、日志位于对应 `runs/logs/framework/register_probe/`。
测试通过只表示读写和正向对照正常、观察过程完成，不代表已证明下面的规范解释。

## 方向切换后的数据

先设为输出并写 0xA5，DATA 和引脚均为 0xA5。
再设为输入、输入引脚固定为 0，写 DATA=0x3C，此时 DATA 读回 0。
最后不再写 DATA，只把 TRI 改回输出，DATA 和引脚变为 0x3C。

[PG144 DATA 页](https://docs.amd.com/r/en-US/pg144-axi-gpio/AXI-GPIO-Data-Register-GPIOx_DATA)
说明输入位写入无效。当前参考按“输入位不保存写入”解释，因而期望恢复为 0xA5。
实测更像写入了输出寄存器，只是输入方向时不驱动外部引脚。
手册的“无效”是否仅指当时引脚效果，需要进一步确认；不能仅凭此处差异报确定缺陷。

## 未启用寄存器的读回

关闭通道 2 时，读 `GPIO2_TRI`（0x0C）得到 0xFFFFFFFF，而非 0。
关闭中断、GPIO 处于输出并已写 0xA5 时，读 `IPISR`（0x120）得到 0xA5。
随后向 0x120 写 0x5A，再读 GPIO_DATA 仍为 0xA5，未观察到该写操作改变 DATA。

[PG144 寄存器页](https://docs.amd.com/r/en-US/pg144-axi-gpio/Register-Space)
明确写未实现寄存器读零、写入无效。读回结果与此不符，写入对照则符合。
还需确认该版本的地址译码范围和是否已有厂商说明；目前保留失败和原始证据。

## 已排除的误判

PG144 DATA 页仍写输出位读零，但生成 IP 附带的
`doc/axi_gpio_v2_0_changelog.txt` 记载 2017.1、修订 14 增加了输出数据读回。
本机为修订 37，因此输出读回写入值不是新 bug，参考模型按该变更检查。
文件作为 `ip_changelog` 随每个自检产物归档，不复制厂商模型到仓库。

接入早期还修正了固定方向 TRI 初值、单通道中断有效位和采样过早的模型/测试错误。
当前每次操作后等待 64 周期才比较状态，不据此判断响应延迟是否达标。
早期失败日志保留；不能把修正前的全部差异累加为独立缺陷数量。

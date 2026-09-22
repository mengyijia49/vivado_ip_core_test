# AXI-Stream 位宽转换器

对应 `xilinx.com:ip:axis_dwidth_converter:1.1`，使用行为仿真模型。
创建、testbench 生成和 XSim 仍从框架的统一入口调用。

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type axis_dwidth_converter
```

## 参数和用例

常用配置有 8 组：1:4、8:2、3:5、5:3、7:7、64:1、1:64，以及不带包尾的 3:4。
包括没有输入 TKEEP 但自动增加输出 TKEEP 的情形。

`configs/ip/axis_dwidth_converter/extended.json` 有 5053 组可选参数。
输入和输出各取 25 种字节宽度，覆盖 1 到 512 及二次幂附近；
分别搭配无侧带、包尾、部分字节、ID/DEST、每字节 TUSER 等组合。
另有 TUSER 最大值附近的配置，总宽度不得超过工具允许的 4096 位。
这只是可选范围，不表示全部通过了 Vivado。

```bash
python3 scripts/run_all.py --config configs/ip/axis_dwidth_converter/extended.json --list-cases
python3 scripts/run_all.py --config configs/ip/axis_dwidth_converter/extended.json --limit 3
```

## 检查什么

参考模型比较字节和包尾序列，不照抄 DUT 的输出打包方式。
细节见[字节级检查](../../protocols/axis_byte_stream.md)。
输入含转换分组边界附近的包长、逐字节有效、位置字节、空传输和连续空包，
并改变 TUSER、TID、TDEST，施加输入间隔和输出回压。

每个配置读取 XCI，严格核对参数、端口和实际生成的输入输出宽度。
没有 TLAST 时，目前只发完整字节，并把最后一组同 ID/DEST 的输入补齐，
避免结束在无法释放的半组数据上。这一模式尚未测试稀疏字节。

暂不使用 ACLKEN，不测试运行中复位。宽位和互质比例会产生较多字节条目，
实际工作量不等于配置里的数值样本预算，运行前应预留时间与磁盘。
能力范围可对照 [PG085 功能说明](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/Overview-of-Features)。

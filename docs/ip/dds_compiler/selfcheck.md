# DDS Compiler 相位自检

`dds_compiler` 对应 `dds_compiler:6.0`。当前只测试单通道固定步进的相位发生器，
不生成正弦和余弦。

```bash
python3 scripts/run_all.py --ip-type dds_compiler
python3 scripts/run_all.py --config configs/ip/dds_compiler/extended.json --list-cases
```

## 检查方法

Python 保存一个无符号相位累加值。每次输出握手成功后，相位按 `PINC` 增加，
结果按相位位宽回绕；输出值再加固定 `POFF`，同样按位宽回绕。
参考模型不读取 Vivado 输出，也不调用厂商模型。

testbench 逐拍检查 `m_axis_phase_tvalid` 和有效相位。`TREADY=0` 时，
有效信号和相位必须保持。`TVALID=0` 时，`TDATA` 没有协议意义，因此只保存原始值，
不参与数值比较。

`aresetn` 是核内寄存的同步复位。模型按实测接口时序保留一拍进入延迟，
并要求复位至少保持两个周期。这与 [PG141 复位说明](https://docs.amd.com/r/en-US/pg141-dds-compiler/Resets)
和[端口说明](https://docs.amd.com/r/en-US/pg141-dds-compiler/Port-Descriptions)一致。

## 配置范围

常用配置有 3 组：8 位正向步进、8 位带相偏的反向等效步进、16 位最大步进。
大矩阵有 96 组，组合 3、4、8、16、32、48 位相位，以及零、小步进和固定相偏。
每组包含启动、回绕、连续输出、长回压、复位进入和复位恢复。

目前没有测试正弦/余弦查表、可编程 PINC/POFF、输入相位、多通道、Resync、ACLKEN、
TLAST 和 TUSER。正弦量化需要单独确定厂商舍入规则，不能直接用宿主浮点函数当作位精确参考。
大矩阵只完成静态校验，未全部运行。

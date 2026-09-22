# AXI Memory Initialization 自检

测试 `axi_memory_init:1.0` 的行为模型。常用配置 6 组，可选矩阵 46080 组。
大矩阵只是后续实验入口，没有全部运行。

IP 在复位后主动向下游内存发起 AXI4 写操作。每个 burst 固定为 16 拍，地址逐段增加，
每拍写入同一个初始化值。全部写响应返回后，IP 才进入普通 AXI4 透传状态。

Python 参考模型独立计算初始化范围、burst 地址、总拍数、初始化数据、`WSTRB` 和
`WLAST`。VHDL testbench 检查以下内容：

- 初始化地址连续，`AWLEN=15`，burst 类型为 INCR，传输尺寸与数据位宽一致；
- 每拍数据和字节使能正确，每 16 拍只出现一次 `WLAST`；
- 地址和数据通道可分别停顿，写响应也可延迟；
- `ACLKEN` 暂停结束后能继续初始化，所有响应完成后才拉高完成信号；
- 进入普通状态后，AW、W、B、AR、R 五个通道及其回压信号原样透传。

参数包括 32 至 1024 位数据、24/32/64 位地址、不同 ID 位宽、初始化范围、基地址、
四种数据图样、回压长度和响应延迟。当前只测试 AXI4 全读写模式，不测试 AXI3、只读、
只写和 USER 字段。

运行常用配置：

```bash
python3 scripts/run_all.py --all --ip-type axi_memory_init
```

# AXI-Stream 数据 FIFO

IP：`xilinx.com:ip:axis_data_fifo:2.0`。这不是 Native FIFO Generator。

```bash
python3 scripts/run_all.py --ip-type axis_data_fifo
```

参数支持 1 至 64 字节、16 至 4096 的二次幂深度、同步或异步时钟、普通或包模式，
存储类型为 auto、block、distributed。Artix-7 配置不开放 UltraRAM。
包模式必须有 TLAST；不启用 ECC、计数和阈值输出。

异步同步级数为 2 至 8；同步模式中的这个字段无实际用途，Vivado 固定为 3，
配置也必须写 3，避免把无效参数变化当成不同实验。

包模式收到 TLAST 或缓冲区达到满条件后可以释放输出。
说明见 [PG085 FIFO 选项](https://docs.amd.com/r/1.1-English/pg085-axi4stream-infrastructure/General-Options)。
目前检查的是完整流的内容、数量、顺序和回压保持，尚未单独断言释放时刻。
输入安排包括深度附近的包长和长回压，实际暂停计数另存文件。
共用规则与其他限制见 [流接口自检](../../protocols/axis_stream.md)。

配置在 `configs/ip/axis_data_fifo/`。常用回归包含同步普通、同步包和异步包三组。

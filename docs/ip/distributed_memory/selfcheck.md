# 分布式存储器自检

配置位于 `configs/ip/distributed_memory/`，IP 为 `dist_mem_gen:8.0`。

- `width`：1 至 256 位。
- `depth`：16 至 4096，须为 16 的倍数，包含 48 这样的非二次幂深度。
- `memory_type`：single_port_ram 或 dual_port_ram。
- `initial_value`：0 至 `2**width-1`，全部地址的初始数据。

当前使用未寄存的输入和异步输出。上升沿按 a、d、we 写入；沿后比较 spo。
双端口模式另有 dpra 和 dpo，是一个写口加两个读地址，不是两个独立写口。
同地址写后读比较更新后的数据；地址只在 0 到 depth-1 内生成。

随机输入前先逐地址读初值、写地址相关数据、读回、写反码、再次读回。
非二次幂深度不使用超范围地址，避免把未定义行为当成 bug。

依据 [PG063](https://docs.amd.com/v/u/en-US/pg063-dist-mem-gen)。
ROM、simple_dual_port_ram、输入输出寄存、双时钟和 COE 文件暂未接入。
大容量参数可用于模型探索，但本框架尚未检查它是否能放入目标 FPGA。

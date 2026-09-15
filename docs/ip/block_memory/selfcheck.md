# 块存储器自检

`block_memory` 对应 `blk_mem_gen:8.4`，只运行原生接口的行为模型。

```bash
python3 scripts/run_all.py --ip-type block_memory
python3 scripts/run_all.py --config configs/ip/block_memory/extended.json --list-cases
```

## 当前检查

- 单端口 RAM、简单双端口 RAM、真双端口 RAM；双端口使用同一个时钟。
- 读优先、写优先、写时保持；字节写支持每字节 8 位或 9 位。
- 初始化、全地址写后读、地址边界、写使能、输出寄存器、REGCE 和同步复位。
- 随机阶段结束后再次读遍地址，检查未被覆盖的存储内容。
- 双端口同址写入不同字节、重叠字节，以及冲突后的确定写入恢复。

Python 分别保存存储内容、输出锁存器和可选输出寄存器。
每个采样周期的期望值先于仿真生成，不读取 DUT 输出来修改期望值。
实际 XCI 的端口、寄存选项和初始化值必须与请求一致。

## 哪些结果不比较

按 [PG058](https://docs.amd.com/v/u/en-US/pg058-blk-mem-gen) 的写模式和碰撞规则：
字节写不能搭配 NO_CHANGE；字节写的 WRITE_FIRST 同周期输出不保证有效。
双端口同址写入时，重叠字节可能不确定；某些同址读写模式也没有确定读值。
参考模型逐位记录这些范围，仍检查其余有效位和后续读回。
详见[有效位比较](../../protocols/defined_output_bits.md)。

## 范围限制

目前宽度为 1 至 256 位，深度为 2 至 4096。大矩阵选择其中 12320 组参数，
不是这些组合都已通过 Vivado。常用回归有 7 组。
当前器件为 Artix-7；简单双端口固定同步读优先，复位优先级固定 CE。
不含异宽端口、独立时钟、ECC、AXI 存储映射接口和物理时序碰撞检查。
官方行为模型本身不精确模拟所有碰撞，不能用这里的 PASS 推断物理存储器表现。

# AXI BRAM Controller 自检

本模块测试 `axi_bram_ctrl:4.1` 的 AXI4-Lite 接口和内部 BRAM。它不是再次测试
`blk_mem_gen` 的原生端口，而是检查 AXI 请求经过控制器后能否正确读写存储器。

当前配置固定使用 32 位 AXI4-Lite，深度可选 1024 到 262144 字，覆盖单端口和双端口
内部 BRAM。常用配置有 4 组，扩展配置有 18 组。

Python 模型按地址保存 32 位数据，并按 `WSTRB` 的四个字节选通信号更新内容。定向序列
检查空存储器读回、首尾和相邻地址、全部 16 种字节选通、不同 `AWPROT/ARPROT`、
写响应和读响应回压，以及 AXI 复位后 BRAM 内容保持。期望值不从 Vivado 输出反推。

AXI BRAM Controller 不做地址译码，地址范围由接口宽度限定。PG078 说明 AXI4-Lite
操作受支持，BRAM 内容不会因为 AXI 接口复位而被清空：
https://docs.amd.com/api/khub/documents/SfuLH0ncggtD5bv~5kHvuw/content

当前还没有接入 AXI4 的多拍 burst、窄传输、非对齐传输、ID 和 ECC。这些功能不能算作
已覆盖，也不能用本模块的 AXI4-Lite 结果推断其正确性。

2026.1 全量运行中的四组常用配置、12 个阶段全部通过，
见[运行记录](../../experiments/vivado_2026_full_regression.md)。
这不表示未运行的大矩阵参数和未接入功能都正确。

# FIFO 计数与阈值

使用同一时钟、等宽数据端口、同步复位，不增加输出寄存器。
`status.py` 在数据队列模型上检查可选输出，不读取 DUT 输出来生成期望值。

```bash
python3 scripts/run_all.py --config configs/ip/fifo_generator/regression/status.json
```

## 参数

| 参数 | 含义 |
| --- | --- |
| data_count_width | 0 关闭；非零时指定计数端口位宽 |
| prog_full_assert | 0 关闭 prog_full；非零时指定置位阈值 |
| prog_full_negate | 0 使用单阈值；非零时指定滞回撤销阈值 |
| prog_empty_assert | 0 关闭 prog_empty；非零时指定置位阈值 |
| prog_empty_negate | 0 使用单阈值；非零时指定滞回撤销阈值 |

这些都是 IP 生成时的常量，不是在仿真过程中修改的阈值输入端口。
`prog_full`、`prog_empty` 始终高有效，不受 `active_low_flags` 影响。

设配置深度为 D：

| 范围 | 标准读 | FWFT |
| --- | --- | --- |
| data_count_width | 1 至 log2(D) | 1 至 log2(D)+1 |
| 单阈值 full | 3 至 D-2 | 5 至 D-1 |
| 单阈值 empty | 2 至 D-3 | 4 至 D-1 |

滞回 full 的撤销阈值必须在上述范围内，并小于置位阈值；
滞回 empty 的撤销阈值必须在上述范围内，并大于置位阈值。
范围来自本机 2025.2 Catalog 的参数校验，生成后还会核对 XCI 和实际端口。

## 比较规则

计数使用已接受写入减去已接受读出的条目数。窄端口去掉低位，不是保留低位。
标准模式写满时计数总线变为零，要结合 full 判断；这不是计数器溢出 bug。
该行为见 [XAPP992 第 1 页](https://docs.amd.com/api/khub/documents/gAWhyWjLZl6LiYC3doWBgw/content)。
FWFT 计数包含尚未到达输出的数据，所以 count 大于零时 empty 仍可能有效。

阈值标志比条目数变化晚一拍。full 在达到置位阈值时有效，低于撤销阈值时无效；
empty 在不超过置位阈值时有效，超过撤销阈值时无效。中间区间保留旧状态。
同步复位把计数清零，prog_full 置零，prog_empty 置一。

定向测试在阈值上下往返，包含等于边界、跨过边界、停顿、同时读写和复位。
计数和两个阈值标志每拍都比较，没有给这些输出加掩码。

## 文档歧义

[PG057](https://docs.amd.com/api/khub/documents/Ds0JjAYlvIFpRMxJMOrbRw/content)
的阈值正文说明一拍更新，但表 3-14 把标准模式写入对 prog_empty 的延迟列为零。
固定输入实测与正文的一拍行为一致，模型按正文检查。

同一手册的表 3-3 列出空 FIFO 的准确计数为 2，正文又说共同时钟 data_count
从写侧看准确。本配置的固定输入记录显示：未消费的数据才计数，读完后为零；
首字到达前，计数可以比可读数据多两项。模型按正文的写侧定义检查。
这两处保留为文档歧义，不计作已确认的 IP bug。

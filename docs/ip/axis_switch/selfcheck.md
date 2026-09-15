# AXI-Stream Switch 自检

`axis_switch` 根据 TDEST 把输入送到指定输出，多路输入可竞争同一个输出。
使用静态路由和完整连接，只做行为仿真。

## 运行

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type axis_switch
python3 scripts/run_all.py --config configs/ip/axis_switch/extended.json --list-cases
python3 scripts/run_all.py --config configs/ip/axis_switch/extended.json --limit 3
```

常用配置有 10 组，大矩阵有 93972 组，后者没有全部运行。
`matrices/` 分开保存路由、仲裁、交叉连接、侧带和字节限定参数。
支持 1 至 16 个输入和输出，但不测一进一出；数据最多 512 字节，
USER 最多 4096 位，ID 和 DEST 最多 32 位。

## 怎么检查

1. Python 按目的地址范围独立计算输出端口，数据和侧带应原样保留。
2. 每路输入独立发数和等待握手；每路输出有独立回压。
3. 按“输入来源、输出端口”分别排队比较，不强行规定不同输出之间的完成顺序。
4. 检查未知值、错误路由、数据或侧带变化、同一队列乱序、漏发、重发和回压保持。
5. 输入握手与输出收包分别计数，禁止没有输入就产生输出；合法目的地址不得报译码错。
6. 仿真结束后，Python 再比较实际收发文件和参考文件。

译码范围和仲裁选项依据 [PG085 路由说明](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/Routing)
及[数据流设置](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/Data-Flow-Properties)。
配置覆盖轮询、固定优先级、真轮询，以及按传输数、包尾、空闲周期释放仲裁。
当前检查数据安全性和有限测试内能否收齐，不逐周期判断谁应该获胜，也不证明公平性。

## 输入覆盖

DATA、USER 或 ID 中选一个字段，低位保留来源编号，其余位由生成策略选择。
保留位数为输入路数向上取整的二进制位数；至少还需一位可变数值。
因此数值覆盖率只针对剩余字段，不是完整接口空间或内部状态覆盖率。

定向输入包含全零、全一、逐位 1 和逐位 0。
路由序列先让各路竞争同一输出，再分散到不同输出，并访问各范围的下界、上界和中点。
传输次数仲裁保持目的地址至少一个配额；按包尾仲裁使用 1、2、3、7、16、32 拍包。
数值预算不足时补齐路由序列；`prepared_additional_groups` 记录额外组数，
`directed_routing_minimum_groups` 记录完成这段路由序列所需的最少组数。
KEEP、STRB 始终全 1，不包含稀疏字节。回压和竞争的实际计数见 `protocol_summary.txt`。

## 文件

文件位于本批时间目录 `axis_switch/<case_id>/`，内部继续按来源和输出端口划分：

| 文件 | 内容 |
| --- | --- |
| `vectors/inputs/s00/input.txt`、`gaps.txt` | 第 0 路输入及间隔；输入行头另带计划输出编号 |
| `vectors/outputs/s00/m00.txt` | 第 0 路送往输出 0 的参考队列 |
| `outputs/inputs/s00/accepted.txt`、`handshakes.txt` | 实际接收值及每次有效输入的握手记录 |
| `outputs/streams/s00/m00.txt` | 对应队列的实际输出，报错前刷新 |
| `outputs/protocol_events.txt` | 带周期号的真实输出事件，包括回压中的值 |
| `vectors/schedule.json` | 每路间隔、路由范围及输出行与输入组的对应关系 |

成功后按来源、输出端口、队列内序号合并为 `actual_output.txt`，每行是一笔输出。
这不是全局完成时间排序。`accepted_input.txt` 则按来源合并，每行是一笔输入。
失败时合并文件可能为空，先看逐路文件和事件日志，不要误以为仿真没有运行。

## 未覆盖

尚未测试 AXI-Lite 动态路由、部分连接、请求抑制、外部仲裁、ACLKEN、运行中复位、
无数值字段的接口、非法目的地址的丢弃规则，以及每种仲裁算法的精确授权次序。
没有把这些未覆盖项算作通过。接入证据见[验收记录](../../experiments/axis_switch_acceptance.md)。

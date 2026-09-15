# AXI-Stream 汇合器自检

`axis_combiner` 将多路窄输入合成一路宽输出。只做行为仿真。

## 运行

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type axis_combiner
python3 scripts/run_all.py --config configs/ip/axis_combiner/extended.json --list-cases
python3 scripts/run_all.py --config configs/ip/axis_combiner/extended.json --limit 3
```

常用回归 10 组，大矩阵 37160 组。不同输入路数的数据矩阵分别存放，
纯侧带配置按 USER、ID、DEST 和完整侧带分文件。不自动重复种子或时序。

## 检查什么

[PG085](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/AXI4-Stream-Combiner?contentId=egtotfYg4MCrFn32jy_dhQ)
规定 DATA、KEEP、STRB、USER 按输入路拼接；LAST、ID、DEST 取自主输入。
Python 独立计算拼接和选择结果，物理端口最低一段对应输入第 0 路。

每组测试从各路各位的单独翻转开始，再发送策略选出的数值。
各路的包尾位置故意不同，用来检查主输入选择，最后一组所有路同时结束包。
每路有自己的间隔，安排每一路单独先到、单独最后到，然后加入随机间隔。
发出 VALID 后，数据保持到握手；各路都接收完本组才开始下一组。
输出端单独回压，不要求它与输入的暂停同步。

testbench 检查输出数值、侧带和顺序，也检查：

- 输入尚未全部提供时不能出现输出。
- 输出握手时，每路都应已接收相应输入；同一沿完成的握手也计入。
- 回压期间 VALID 和数据不能变化。
- 未知值、多余输出和超时应报错。

实际接收的输入另存文件，Python 再与计划输入比较，避免驱动接错却误判 IP。
故意出错的独立 VHDL 电路用于检查这些报错路径，不计作厂商 IP bug。

## 参数和文件

输入路数 2 至 16，每路 DATA 字节数乘路数不超过 512。
ID、DEST 每路 0 至 32 位；本机 Catalog 接受 USER 每路 0 至 4096 位。
无 DATA 时禁用 KEEP、STRB，至少保留一个数值字段。
主输入编号从 0 开始，小于路数；没有 LAST、ID、DEST 时固定为 0。
DATA 范围依据 [PG085 参数说明](https://docs.amd.com/r/en-US/pg085-axi4stream-infrastructure/Signal-Properties?contentId=gWK1P_lJvAoMKpgPRECHcA)。

文件保存在本批时间目录 `axis_combiner/<case_id>/`：

- `input_vectors.txt`、`accepted_input.txt`：一行一组，从左至右为第 0 路、第 1 路等。
- `expected_output.txt`、`actual_output.txt`：一行一个合成输出，字段顺序见 manifest 中的 testbench。
- `gaps.txt`：一行一组，每列对应一路，列号从 0 开始。
- `schedule.json`：保存全部路的间隔和原始数值排列。
- `protocol_events.txt`：逐周期记录各路 VALID/READY 和有效输出。
- `protocol_summary.txt`：各路接收数、暂停数、输出数及只有部分输入有效的周期数。

输入组数不是各路接收数之和。大位宽会明显增加磁盘开销：
16 路各 4096 位 USER 的逐位前缀就有约 13 万组，每份输入或输出文本约 8.6 GB，
还未计算日志和归档副本。不要直接全跑最大矩阵。

## 限制

KEEP、STRB 目前只发送全 1。仅启动时复位，暂不测运行中复位、ACLKEN 和 `s_cmd_err`。
输入组之间不交叉发送，尚未测试不同组在各路上任意超前积压。
穷举配置只穷举数值字段，不穷举全部时序和包尾排列。
PASS 只说明这批测试未发现异常；接入证据见[验收记录](../../experiments/axis_combiner_acceptance.md)。

# AXI to LMB Bridge 自检

## 怎么运行

先加载 Vivado 环境，再运行这类 IP 的常用配置：

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type axi_lmb_bridge
```

大矩阵有 192 组参数。只试前几组时运行：

```bash
python3 scripts/run_all.py --config configs/ip/axi_lmb_bridge/extended.json --limit 3
```

## 检查内容

Python 参考模型先把 AXI4 读写事务换算成应出现的 LMB 访问。VHDL testbench 再逐笔检查
LMB 地址、读写方向、写数据、字节使能和保护位，同时记录 AXI 的读写响应。

定向输入包含单拍和多拍读写、Fixed、Increment、Wrap burst、窄传输、W 先于 AW、
零字节使能、LMB 等待、地址错误、不可纠正错误和输出回压。启用 Pause 的配置还会检查
接口停止接收并给出 `Pause_Ack`。测试台也检查响应在回压期间不能变化。

常用回归有 5 组，覆盖 32/64 位数据、32/40/64 位地址、不同 ID 位宽、Standard 和
Frequency 两种 LMB 协议、保护信号及 Pause。大矩阵把这些参数交叉成 192 组。

## 当前结果和限制

2026-09-23 在 Vivado 2026.1 上复测全部 5 组常用配置，15 个阶段均通过。
此前两组 Frequency 配置的数据和响应差异来自测试端：读数据和读 UE 应比 Ready 晚一拍，
旧模板没有做这个区分。修正后原输入、原期望值通过；Standard 和 Frequency 的固定请求
对照也通过。这条已排除出 IP bug 候选，过程和日志见[排查记录](data_issue.md)。

当前 FIFO 深度固定为 AW=2、W=8、AR=2、R=8，没有作为扫描参数。测试只发送合法 burst，
没有覆盖多个未完成事务的全部交错次序，也没有做综合、实现或板级测试。

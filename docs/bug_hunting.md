# 发现异常后怎么排查

一次失败先作为待查问题，不直接记为 IP bug。
环境、参数、testbench 和 Python 参考模型都可能导致失败。

## 找到出错位置

1. 在本批 `report.csv` 找到失败配置和阶段。
2. 打开该行的日志。创建失败先查参数、工具和许可证；仿真失败再查编译、展开和运行日志。
3. 自检失败时查看 `outputs/failure.json`，其中记录首个差异、缺失/额外输出或未知位，状态为 `UNTRIAGED`。
4. 如果数值文件没有差异，继续查时序断言和超时，不能据此排除故障。

输出序号从 0 开始。启用输入乱序或保持后，不能把输出序号直接当原始输入编号：
要通过 `vectors/schedule.json` 的 `transaction_vector_indices`
查到 `vectors/vectors.json` 中的输入。`failure.json` 会保存可用的映射。

testbench 在停止前写出首个错误值，保留 X、U 等未知状态，不把它们转成零。
Vivado 自身日志缺失时，检查同名 `.process.log` 和 `.invocation.json`。

## 复现和确认

1. 保留原始时间编号，执行 `run.json` 中的 `replay_command`，使用相同 Vivado 环境。
2. 核对 XCI 参数、接口时序和参考计算，先排除测试程序的问题。
3. 对照该版本的官方规范，必要时用独立模型或其他工具交叉检查。
4. 缩短输入序列，确认最少需要哪些输入和间隔才能触发，保留原始与缩减后的序列。
5. 根因确认后再登记为 bug；不同种子触发同一根因只算一个。

当前复现会重跑整个配置，因为错误可能依赖前面的输入。
自动缩减、根因去重和缺陷数据库尚未实现。
开始长期测试的方法见[探索配置](bug_discovery.md)，重跑方法见[复现说明](reproducibility.md)。

## 评价测试方法

后续实验记录确认的独立 bug 数量、首次发现时间、输入数量、误报和重复触发情况。
比较算法时固定 IP、预算和种子集合。现有报告提供输入数、耗时、输入覆盖和异常文件；
确认根因及计算上述全部指标仍需人工完成。

## 检查框架会不会漏报

故障注入测试用故意出错的 DUT，检查未知输出和提前出现的有效信号能否被捕获：

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
VIVADO_INTEGRATION=1 PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_failure_detection.py' -v
```

这些错误用来测试框架，不计入真实 AMD IP bug。

# 卷积编码器自检

## 运行方法

运行四组常用配置：

```bash
python3 scripts/run_all.py --ip-type convolution
```

查看 126 组扩展参数，或选取其中一部分运行：

```bash
python3 scripts/run_all.py --config configs/ip/convolution/extended.json --list-cases
python3 scripts/run_all.py --config configs/ip/convolution/extended.json --limit 4
```

## 检查内容

卷积编码器每次接收一个输入位。这个输入位进入约束寄存器最高位，旧数据向低位移动。
每个输出位都有一个二进制多项式，参考模型取出多项式选中的寄存器位并计算奇偶校验。
多项式 0 对应输出 `tdata(0)`，其余输出依次放在更高位，未使用的输出填充位必须为 0。

配置覆盖 3 至 9 位约束长度和 1/2 至 1/7 输出率。三种多项式族分别从低位、
高位和分散位置选择不同抽头。实际多项式会写入运行清单，便于复查，不从 DUT 输出反推。

定向输入先把状态清零，再发送单脉冲、连续 1 和交替位，让每个历史位置影响输出。
输入总线高 7 位使用不同填充值，检查 IP 是否只读取 `tdata(0)`。公共流接口 testbench
另外检查输入间隔、输出回压、顺序、未知值和停顿期间的数据保持。

2026.1 全量运行中的四组配置、12 个阶段全部通过，
见[运行记录](../../experiments/vivado_2026_full_regression.md)。

## 当前限制

当前只测试非打孔编码。固定打孔、单路串行打孔输出、双路打孔输出、`TLAST` 同步事件和
`ACLKEN` 尚未接入。这里使用的是测试用合法多项式，不表示某一种通信标准的推荐多项式。
126 组扩展参数已通过静态校验，只有四组代表配置实际运行过 Vivado。

测试只运行行为仿真，不包含综合、实现或误码信道中的解码效果。

接口和算法定义参考 [Convolutional Encoder Product Guide PG026](https://docs.amd.com/v/u/en-US/pg026_convolution)。

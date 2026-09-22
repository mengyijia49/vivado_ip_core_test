# AXI Sideband Utility 自检

## 运行方法

运行四组常用配置：

```bash
python3 scripts/run_all.py --ip-type axi_sideband_util
```

查看或抽取大矩阵：

```bash
python3 scripts/run_all.py --config configs/ip/axi_sideband_util/extended.json --list-cases
python3 scripts/run_all.py --config configs/ip/axi_sideband_util/extended.json --limit 4
```

## 检查内容

当前配置使用 AXI4 读写接口。Python 模型逐周期计算 AW、W、B、AR、R 五个通道的输出，
检查地址、数据、ID、响应、突发属性、USER 字段以及 VALID/READY 握手。
定向输入会让每个通道完成传输，也会分别制造上游或下游回压。

SMID 支持三种模式：

- `Bypass`：地址 USER 字段保持不变。
- `Insert`：在 AWUSER 和 ARUSER 低位插入固定 SMID。
- `Remove`：移除 AWUSER 和 ARUSER 低位的 SMID。

常用回归包含 32、64、256 和 1024 位数据通路。大矩阵共有 1152 组，扫描数据宽度、
ID 宽度、地址 USER 宽度、SMID 宽度和固定值。

## 当前限制

本轮没有接入奇偶校验，也没有接入 `Extract` 模式。当前通过结果只说明已运行的配置中，
Python 模型与本次 Vivado 2026.1 行为仿真结果一致，不能说明其他参数已经通过，也不能说明 IP 没有 bug。

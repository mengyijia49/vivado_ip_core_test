# AHB-Lite 到 AXI Bridge 自检

## 检查范围

当前测试把一笔 AHB-Lite SINGLE 传输送入桥接器，再由 testbench 模拟 AXI 从设备。
Python 独立计算期望的 AXI 地址、读写方向、传输尺寸、保护和缓存属性。写操作还检查
数据和 `WSTRB`，读操作检查返回数据。AXI 侧会插入等待，并返回 OKAY、SLVERR 或
DECERR，testbench 检查 AHB 侧的 `HREADYOUT`、`HRDATA` 和 `HRESP`。

常用回归有 6 组，覆盖 32/64 位数据、32/40/64 位地址、不同 AXI ID 宽度、窄传输开关、
安全属性、超时参数以及不同等待周期。可选大矩阵有 7680 组，只做了配置静态校验，
没有全部运行 Vivado。

## 运行方法

```bash
source /data/Xilinx/2026.1/Vivado/settings64.sh
python3 scripts/run_all.py --ip-type ahblite_axi_bridge
```

只运行一个配置：

```bash
python3 scripts/run_all.py --ip-type ahblite_axi_bridge --case ahblite_axi_64_narrow
```

## 已运行配置

2026.1 全量运行中的 6 组常用配置、18 个阶段全部通过，
见[运行记录](../../experiments/vivado_2026_full_regression.md)。
这只表示本批输入没有发现差异，不表示全部参数都正确。

## 当前限制

当前只检查 SINGLE 传输，没有发送 AHB burst、BUSY、锁定传输或触发桥接器超时。
AXI 侧每次只处理一笔事务，也没有检查多笔未完成事务。后续需要这些功能时，应先扩展
独立参考和 testbench，再增加相应配置，不能用现有 PASS 代替这些检查。

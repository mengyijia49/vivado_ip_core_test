# AXI Timebase Watchdog 自检

本模块测试 `axi_timebase_wdt:3.0` 的旧版 watchdog 模式。Python 模型独立维护计数器、
启用位、首次到期状态和复位状态，通过公共 AXI-Lite testbench 访问寄存器。

定向输入检查配置的 `2^N` 周期、首次到期中断、清除到期状态、未清除时第二次到期产生
复位、`freeze` 暂停、运行时修改周期，以及“只允许启用一次”和“允许反复启停”的差别。
测试会轮换全部 `WSTRB`。非完整写选通应返回 `SLVERR` 且不修改寄存器，完整写选通才用于
控制 watchdog。随机输入补充不同暂停长度，AXI-Lite 后端继续检查独立请求、响应回压、
响应保持和 `wdt_reset` 锁存输出。第二次到期后该输出保持为高，外部 AXI 复位后清零。

参数 `interval` 为 8 至 15，对应 256 至 32768 个时钟周期。常用配置有 4 组，扩展
配置有 16 组。

当前没有接入 Window WDT。该模式使用另一套寄存器，还包含第一/第二窗口、失败计数、
任务签名和第二序列计时器，不能用旧版模式的结果代替。测试只运行行为仿真。

Vivado 2026.1 运行了 4 组常用配置，12 个阶段均为 `PASS`，
见[全量报告](../../experiments/vivado_2026_full_regression.md)。

寄存器和周期定义以 AMD PG128 为准：
https://docs.amd.com/v/u/en-US/pg128-axi-timebase-wdt

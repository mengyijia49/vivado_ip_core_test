# Vivado IP Automation Project

目标：
在 Ubuntu 下实现 Vivado IP 的自动化测试流程，不使用 Vivado GUI。

当前已完成：
1. Vivado 环境路径为 /data/Xilinx/2025.2/Vivado/settings64.sh。
2. Python 可以通过 subprocess 调用 vivado -mode batch。
3. Tcl 脚本 tcl/create_divider_ip.tcl 可以自动创建 Divider Generator IP。
4. 当前 Divider 配置为：
   - dividend_and_quotient_width = 16
   - divisor_width = 8
   - remainder_type = Remainder
   - operand_sign = Unsigned
   - FlowControl = NonBlocking
5. scripts/run_all.py 可以调用 Vivado 生成 Divider IP，并将结果写入 reports/report.csv。

工程规则：
1. 不允许依赖 Vivado GUI。
2. Vivado 只能通过 batch Tcl 调用。
3. Python 作为总控脚本。
4. 所有 Vivado 生成文件放入 runs/。
5. 所有日志放入 runs/logs/。
6. 所有报告放入 reports/。
7. 不要手动修改 runs/ 里的 Vivado 生成文件。
8. 每次修改后都要运行：
   python3 -m py_compile scripts/run_all.py
   python3 scripts/run_all.py
9. 失败类型至少包括：
   - VIVADO_NOT_FOUND
   - CREATE_IP_FAILED
   - TIMEOUT
   - LOG_NOT_FOUND
   - LOG_CHECK_FAILED
   - XCI_NOT_FOUND
   - PASS

下一阶段目标：
把单个 Divider 配置扩展成多个 Divider 参数组合批量生成。

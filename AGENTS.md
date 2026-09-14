# Vivado IP 自动测试工程

## 用途和现状

本项目帮助使用者长期测试多种 IP、寻找并复现 bug。使用者计划测试一至两个月，
目标是找到至少 5 个独立 bug；这不是框架已经取得的结果。
PASS 只表示本批测试未发现异常，失败也需要先区分环境、脚本、参考模型和 IP 问题。

当前支持 Divider Generator、Multiplier Generator，默认 6 组配置、19 个阶段。
两类 IP 都有参数化数值自检和 Python 参考模型；divider_u16_u8 另有官方 demo。
已支持多种子、大预算、系统边界、时序扰动、失败记录、归档和续跑。
策略包括 directed_random:1.0、coverage_guided:1.0、exhaustive:1.0。
研究算法和真实 bug 的长期实验尚未完成。

## 工程规则

1. Python 总控，Vivado 只能通过 batch Tcl 调用，不依赖 GUI。
   环境脚本为 /data/Xilinx/2025.2/Vivado/settings64.sh。
2. scripts/run_all.py 是兼容入口，代码位于 src/vivado_ip_test/。
   IpBuilder、TestbenchGenerator、SimulationRunner 分别统一负责创建、生成和仿真。
   仿真 Tcl 统一使用 tcl/run_xsim_batch.tcl。
3. 根据 ip_type 选择插件，不根据 case_id 猜测 IP 类型。
   StrategyRegistry 统一选择策略，RunRecorder 统一保存运行记录。
4. 不同 IP 的配置、参数 schema、Tcl、模板、测试和专属文档分目录维护。
   公共配置用 includes 引用单类 IP 配置，不混放各 IP 的参数。
5. 所有运行产物放入 runs/，日志放入 runs/logs/，报告放入 reports/。
   每次运行的目录须含本地日期、时分秒和时区，并避免重名覆盖。
   工程位于 runs/batches/<run_id>/<ip_type>/<case_id>/。
   日志位于 runs/logs/batches/<run_id>/<ip_type>/<case_id>/。
   报告位于 reports/history/<run_id>/，reports/latest 只作符号链接。
6. 不手动修改 runs/ 中的 Vivado 生成文件，不改写历史证据。
   旧产物迁移须核对移动前后的内容。
7. Markdown 使用平实、简短的中文。直接说明做法、结果和限制，
   不堆砌术语，不重复陈述目标；命令、路径和协议名称保留原文。

## 修改后检查

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
python3 -m py_compile scripts/run_all.py
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/run_all.py
```

保留以下状态，不合并或删掉失败分类：

- VIVADO_NOT_FOUND
- CREATE_IP_FAILED
- TIMEOUT
- LOG_NOT_FOUND
- LOG_CHECK_FAILED
- XCI_NOT_FOUND
- TESTBENCH_GENERATION_FAILED
- SIMULATION_FAILED
- VERIFICATION_FAILED
- PASS

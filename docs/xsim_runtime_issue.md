# XSim 早期失败记录

## 观察到的情况

2026-09-14，最小 VHDL 和 Divider demo 都曾在加载快照时出现：

```text
ERROR: unexpected exception when evaluating tcl command
```

位置在 `xsim.dir/tb_behav/xsim_script.tcl` 的加载命令。
发生错误时 XSim 仍可能返回 0，不能只看返回码。

用户在普通终端运行最小 smoke test 成功。当天 17:44，
取消执行限制后复用原最小快照也成功，没有修改 VHDL 或重新展开。
当时命令如下，其中日志后来作为旧文件归档：

```bash
source /data/Xilinx/2025.2/Vivado/settings64.sh
cd /tmp/xsim_smoke2
xsim tb_behav -R -log /home/dpc/vivado_ip_auto_test/runs/logs/xsim_smoke_recheck.log
```

输出含 `Note: XSIM_SMOKE_OK`，返回 0。
因此不能认定 XSim 安装整体损坏。执行环境差异是排查方向，
但没有定位到具体系统调用或资源限制。

## 后来处理了什么

旧执行器超时后可能留下 Vivado/XSim 后代进程。现在每条命令独立启动进程组，
超时或 Python 异常退出时清理整组进程，单元测试也检查了孙进程退出。

正式仿真使用 `tcl/run_xsim_batch.tcl`：
先 `launch_simulation -scripts_only`，再手动编译、展开和运行 XSim。
检查捕获输出及非空的 simulate.log，不依赖交互式 launch/run 路径。

官方 demo 用 severity failure 正常结束，所以 Tcl 根据成功和真实错误标记判断。
Python 要求外层返回码为 0、有完整 PASS 行、无完整 FAIL 行，
不把回显的 Tcl 源码当错误输出。

## 再次失败时

1. 检查本批 `runs/logs/batches/<run_id>/<ip_type>/<case_id>/` 的阶段日志和进程记录。
2. 检查工程 `behav/xsim/` 下的 simulate.log、xsimcrash.log、xsimkernel.log；缺失或空文件也要记录。
3. 用相同最小快照比较普通终端和原执行环境，记录命令与返回码。新诊断产物放在带时间编号的目录。
4. 最小测试通过而 IP 失败时，再查编译库、展开日志、top、参数和 testbench 断言。
5. 确认没有旧进程仍在使用同一工程，不要仅凭一条异常判断安装损坏。

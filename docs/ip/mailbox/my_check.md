![image-20260923121926917](/home/dpc/.config/Typora/typora-user-images/image-20260923121926917.png)

mailbox_tlast_check

xc7a35tcsg324-1

Mailbox

dut_0

![image-20260923121907751](/home/dpc/.config/Typora/typora-user-images/image-20260923121907751.png)

![image-20260923121946021](/home/dpc/.config/Typora/typora-user-images/image-20260923121946021.png)

![image-20260923122003058](/home/dpc/.config/Typora/typora-user-images/image-20260923122003058.png)

![image-20260923122015399](/home/dpc/.config/Typora/typora-user-images/image-20260923122015399.png)

![image-20260923122028180](/home/dpc/.config/Typora/typora-user-images/image-20260923122028180.png)

C_DEPTH

file actual_file : text open write_mode is

file actual_file : text open write_mode is "mailbox_manual_actual_output.txt";



![image-20260923123840530](/home/dpc/.config/Typora/typora-user-images/image-20260923123840530.png)



(this image is hard to understand.)



logs:

restart
INFO: [Wavedata 42-604] Simulation restarted
run all
Error: MAILBOX_AXIS_TLAST_MISMATCH actual='0' expected='1'
Time: 525 ns  Iteration: 0  Process: /tb_mailbox_axis_selfcheck/stimulus  File: /home/dpc/mailbox_tlast_check/mailbox_tlast_check.srcs/sim_1/imports/tb/tb_mailbox_axis_selfcheck.vhd
Error: MAILBOX_AXIS_TLAST_MISMATCH actual='0' expected='1'
Time: 625 ns  Iteration: 0  Process: /tb_mailbox_axis_selfcheck/stimulus  File: /home/dpc/mailbox_tlast_check/mailbox_tlast_check.srcs/sim_1/imports/tb/tb_mailbox_axis_selfcheck.vhd
Error: MAILBOX_AXIS_TLAST_MISMATCH actual='0' expected='1'
Time: 825 ns  Iteration: 0  Process: /tb_mailbox_axis_selfcheck/stimulus  File: /home/dpc/mailbox_tlast_check/mailbox_tlast_check.srcs/sim_1/imports/tb/tb_mailbox_axis_selfcheck.vhd
Error: MAILBOX_AXIS_TLAST_MISMATCH actual='0' expected='1'
Time: 975 ns  Iteration: 0  Process: /tb_mailbox_axis_selfcheck/stimulus  File: /home/dpc/mailbox_tlast_check/mailbox_tlast_check.srcs/sim_1/imports/tb/tb_mailbox_axis_selfcheck.vhd
Error: MAILBOX_AXIS_TLAST_MISMATCH actual='0' expected='1'
Time: 2155 ns  Iteration: 0  Process: /tb_mailbox_axis_selfcheck/stimulus  File: /home/dpc/mailbox_tlast_check/mailbox_tlast_check.srcs/sim_1/imports/tb/tb_mailbox_axis_selfcheck.vhd
Error: MAILBOX_AXIS_TLAST_MISMATCH on M0 concurrent transfer
Time: 2235 ns  Iteration: 0  Process: /tb_mailbox_axis_selfcheck/stimulus  File: /home/dpc/mailbox_tlast_check/mailbox_tlast_check.srcs/sim_1/imports/tb/tb_mailbox_axis_selfcheck.vhd
Error: MAILBOX_AXIS_TLAST_MISMATCH on M1 concurrent transfer
Time: 2255 ns  Iteration: 0  Process: /tb_mailbox_axis_selfcheck/stimulus  File: /home/dpc/mailbox_tlast_check/mailbox_tlast_check.srcs/sim_1/imports/tb/tb_mailbox_axis_selfcheck.vhd
Error: MAILBOX_AXIS_TLAST_MISMATCH on M0 concurrent transfer
Time: 2285 ns  Iteration: 0  Process: /tb_mailbox_axis_selfcheck/stimulus  File: /home/dpc/mailbox_tlast_check/mailbox_tlast_check.srcs/sim_1/imports/tb/tb_mailbox_axis_selfcheck.vhd
Error: MAILBOX_AXIS_TLAST_MISMATCH on M1 concurrent transfer
Time: 2325 ns  Iteration: 0  Process: /tb_mailbox_axis_selfcheck/stimulus  File: /home/dpc/mailbox_tlast_check/mailbox_tlast_check.srcs/sim_1/imports/tb/tb_mailbox_axis_selfcheck.vhd
Error: MAILBOX_AXIS_TLAST_MISMATCH on M0 concurrent transfer
Time: 2335 ns  Iteration: 0  Process: /tb_mailbox_axis_selfcheck/stimulus  File: /home/dpc/mailbox_tlast_check/mailbox_tlast_check.srcs/sim_1/imports/tb/tb_mailbox_axis_selfcheck.vhd
Error: MAILBOX_AXIS_TLAST_MISMATCH on M0 concurrent transfer
Time: 2385 ns  Iteration: 0  Process: /tb_mailbox_axis_selfcheck/stimulus  File: /home/dpc/mailbox_tlast_check/mailbox_tlast_check.srcs/sim_1/imports/tb/tb_mailbox_axis_selfcheck.vhd
Error: MAILBOX_AXIS_TLAST_MISMATCH on M1 concurrent transfer
Time: 2395 ns  Iteration: 0  Process: /tb_mailbox_axis_selfcheck/stimulus  File: /home/dpc/mailbox_tlast_check/mailbox_tlast_check.srcs/sim_1/imports/tb/tb_mailbox_axis_selfcheck.vhd
Note: MAILBOX_AXIS_SELF_CHECK_STATUS: FAIL TLAST was not preserved
Time: 2745 ns  Iteration: 0  Process: /tb_mailbox_axis_selfcheck/stimulus  File: /home/dpc/mailbox_tlast_check/mailbox_tlast_check.srcs/sim_1/imports/tb/tb_mailbox_axis_selfcheck.vhd
$finish called at time : 2745 ns : File "/home/dpc/mailbox_tlast_check/mailbox_tlast_check.srcs/sim_1/imports/tb/tb_mailbox_axis_selfcheck.vhd" Line 219
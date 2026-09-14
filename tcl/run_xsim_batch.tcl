set project_path [lindex $argv 0]
set testbench_path [lindex $argv 1]
set top_name [lindex $argv 2]
set success_marker [lindex $argv 3]
set failure_markers [lrange $argv 4 end]

# 分段构造状态标记，避免 Vivado 回显 Tcl 源码时造成日志误判。
set stage_pass "XSIM_STAGE_STATUS: PA"
append stage_pass "SS"
set stage_fail "XSIM_STAGE_STATUS: FA"
append stage_fail "IL"

proc fail_stage {message marker} {
    puts "ERROR: $message"
    puts $marker
    exit 1
}

if {$project_path eq "" || $testbench_path eq "" ||
    $top_name eq "" || $success_marker eq ""} {
    fail_stage "缺少 XSim 仿真参数。" $stage_fail
}
if {![file exists $project_path]} {
    fail_stage "Vivado 工程不存在：$project_path" $stage_fail
}
if {![file exists $testbench_path]} {
    fail_stage "testbench 不存在：$testbench_path" $stage_fail
}

if {[info exists env(LIBRARY_PATH)]} {
    unset env(LIBRARY_PATH)
}

open_project $project_path
set_property target_simulator XSim [current_project]
set simset [get_filesets sim_1]

if {[llength [get_files -quiet $testbench_path]] == 0} {
    add_files -fileset $simset -norecurse $testbench_path
}

set extension [string tolower [file extension $testbench_path]]
if {$extension eq ".vhd" || $extension eq ".vhdl"} {
    set_property file_type {VHDL 2008} [get_files $testbench_path]
}
set_property top $top_name $simset
set_property top_lib xil_defaultlib $simset
update_compile_order -fileset $simset

set project_dir [file dirname $project_path]
set project_name [file rootname [file tail $project_path]]
set sim_dir "$project_dir/${project_name}.sim/sim_1/behav/xsim"
if {[file isdirectory $sim_dir]} {
    file delete -force $sim_dir
}

set script_status [catch {
    launch_simulation -simset sim_1 -mode behavioral -scripts_only
} script_msg]
if {$script_msg ne ""} {
    puts $script_msg
}
if {$script_status != 0} {
    fail_stage "launch_simulation -scripts_only 执行失败。" $stage_fail
}
if {![file isdirectory $sim_dir]} {
    fail_stage "未生成 XSim 仿真目录：$sim_dir" $stage_fail
}

set old_dir [pwd]
cd $sim_dir

set compile_status [catch {exec bash compile.sh 2>@1} compile_msg]
puts $compile_msg
if {$compile_status != 0} {
    cd $old_dir
    fail_stage "XSim 编译失败。" $stage_fail
}

set elaborate_status [catch {exec bash elaborate.sh 2>@1} elaborate_msg]
puts $elaborate_msg
if {$elaborate_status != 0} {
    cd $old_dir
    fail_stage "XSim elaboration 失败。" $stage_fail
}

set batch_tcl "$sim_dir/run_batch.tcl"
set simulate_log "$sim_dir/simulate.log"
set fh [open $batch_tcl w]
puts $fh "run all"
puts $fh "quit"
close $fh

set snapshot "${top_name}_behav"
set simulation_key "Behavioral:sim_1:Functional:$top_name"
set sim_command [list xsim $snapshot \
    -key $simulation_key \
    -tclbatch $batch_tcl \
    -log simulate.log]
set sim_status [catch {exec {*}$sim_command 2>@1} sim_msg]
puts $sim_msg
cd $old_dir

set simulate_text ""
if {[file exists $simulate_log] && [file size $simulate_log] > 0} {
    set fh [open $simulate_log r]
    set simulate_text [read $fh]
    close $fh
}

set combined_text "$sim_msg\n$simulate_text"
set has_success [expr {[string first $success_marker $combined_text] >= 0}]
set has_failure 0
foreach marker $failure_markers {
    if {$marker ne "" && [string first $marker $combined_text] >= 0} {
        set has_failure 1
        break
    }
}

# testbench 可通过 severity failure 正常结束，因此不单独使用 sim_status 判定。
if {$has_success && !$has_failure} {
    puts "XSim simulation completed successfully."
    puts $stage_pass
    exit 0
}

puts "ERROR: XSim 仿真未报告干净的成功结果。"
puts "XSim catch status: $sim_status"
puts $stage_fail
exit 1

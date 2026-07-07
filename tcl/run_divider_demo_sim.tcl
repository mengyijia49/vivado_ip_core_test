set run_dir [lindex $argv 0]
set sim_demo_pass "SIM_DEMO_STATUS: PA"
append sim_demo_pass "SS"
set sim_demo_fail "SIM_DEMO_STATUS: FA"
append sim_demo_fail "IL"

if {$run_dir eq ""} {
    puts "ERROR: run_dir argument is empty."
    puts $sim_demo_fail
    exit 1
}

set proj_path "$run_dir/proj/divider_ip_test.xpr"
set tb_path "$run_dir/proj/divider_ip_test.gen/sources_1/ip/div_gen_0/demo_tb/tb_div_gen_0.vhd"

if {![file exists $proj_path]} {
    puts "ERROR: project not found: $proj_path"
    puts $sim_demo_fail
    exit 1
}

if {![file exists $tb_path]} {
    puts "ERROR: demo testbench not found: $tb_path"
    puts $sim_demo_fail
    exit 1
}

puts "Run dir: $run_dir"
puts "Project: $proj_path"
puts "Demo testbench: $tb_path"

if {[info exists env(LIBRARY_PATH)]} {
    unset env(LIBRARY_PATH)
}

open_project $proj_path

set_property target_simulator XSim [current_project]
set simset [get_filesets sim_1]

if {[llength [get_files -quiet $tb_path]] == 0} {
    add_files -fileset $simset -norecurse $tb_path
}

set_property top tb_div_gen_0 $simset
set_property top_lib xil_defaultlib $simset
update_compile_order -fileset $simset

set script_status [catch {launch_simulation -simset sim_1 -mode behavioral -scripts_only} script_msg]
if {$script_msg ne ""} {
    puts $script_msg
}
if {$script_status != 0} {
    puts "ERROR: launch_simulation scripts_only failed."
    puts $sim_demo_fail
    exit 1
}

set sim_dir "$run_dir/proj/divider_ip_test.sim/sim_1/behav/xsim"
set batch_tcl "$sim_dir/run_demo_batch.tcl"
set simulate_log "$sim_dir/simulate.log"

if {![file isdirectory $sim_dir]} {
    puts "ERROR: simulation directory not found: $sim_dir"
    puts $sim_demo_fail
    exit 1
}

set old_dir [pwd]
cd $sim_dir

set compile_status [catch {exec bash compile.sh 2>@1} compile_msg]
puts $compile_msg
if {$compile_status != 0} {
    cd $old_dir
    puts "ERROR: XSim compile failed."
    puts $sim_demo_fail
    exit 1
}

set elaborate_status [catch {exec bash elaborate.sh 2>@1} elaborate_msg]
puts $elaborate_msg
if {$elaborate_status != 0} {
    cd $old_dir
    puts "ERROR: XSim elaborate failed."
    puts $sim_demo_fail
    exit 1
}

set fh [open $batch_tcl w]
puts $fh "run all"
puts $fh "quit"
close $fh

set sim_status [catch {
    exec xsim tb_div_gen_0_behav \
        -key {Behavioral:sim_1:Functional:tb_div_gen_0} \
        -tclbatch $batch_tcl \
        -log simulate.log 2>@1
} sim_msg]
puts $sim_msg

cd $old_dir

set simulate_text ""
if {[file exists $simulate_log] && [file size $simulate_log] > 0} {
    set fh [open $simulate_log r]
    set simulate_text [read $fh]
    close $fh
}

set combined_text "$sim_msg\n$simulate_text"
set has_success [expr {[string first "Test completed successfully" $combined_text] >= 0}]
set has_protocol_error [expr {
    [string first "ERROR: m_axis_dout_tdata is invalid" $combined_text] >= 0 ||
    [string first "ERROR: terminating test with failures." $combined_text] >= 0
}]

if {$has_success && !$has_protocol_error} {
    puts "Divider demo simulation completed successfully."
    puts $sim_demo_pass
    exit 0
}

puts "ERROR: Divider demo simulation did not report a clean success."
puts $sim_demo_fail
exit 1

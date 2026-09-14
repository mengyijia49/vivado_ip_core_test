set run_dir [lindex $argv 0]
set dut_path [lindex $argv 1]
create_project framework_negative "$run_dir/proj" -part xc7a35tcsg324-1 -force
add_files -norecurse $dut_path
set_property file_type {VHDL 2008} [get_files $dut_path]
close_project
exit 0

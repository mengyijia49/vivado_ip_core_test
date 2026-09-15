if {[llength $argv] < 1 || [llength $argv] % 2 != 1} {
    error "Usage: run_dir CONFIG.name value ..."
}
set run_dir [file normalize [lindex $argv 0]]
create_project ip_test "$run_dir/proj" -part xc7a35tcsg324-1 -force
create_ip -vlnv $ip_vlnv -module_name dut_0
set_property -dict [lrange $argv 1 end] [get_ips dut_0]
generate_target all [get_ips dut_0]
export_ip_user_files -of_objects [get_ips dut_0] -no_script -sync -force
if {[info exists post_generate_hook]} {
    {*}$post_generate_hook $run_dir [get_ips dut_0]
}
puts "Configured IP generated successfully."
exit 0

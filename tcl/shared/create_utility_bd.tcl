if {[llength $argv] < 1 || [llength $argv] % 2 != 1} {
    error "Usage: run_dir CONFIG.name value ..."
}
set run_dir [file normalize [lindex $argv 0]]
create_project ip_test "$run_dir/proj" -part xc7a35tcsg324-1 -force
create_bd_design dut_0
set core [create_bd_cell -type ip -vlnv $ip_vlnv core]
set_property -dict [lrange $argv 1 end] $core
foreach pin [get_bd_pins core/*] {
    set name [file tail $pin]
    set args [list -dir [get_property DIR $pin]]
    set left [get_property LEFT $pin]
    if {$left ne ""} {
        lappend args -from $left -to [get_property RIGHT $pin]
    }
    set port [create_bd_port {*}$args $name]
    connect_bd_net $port $pin
}
validate_bd_design
save_bd_design
generate_target all [get_files dut_0.bd]
export_ip_user_files -of_objects [get_files dut_0.bd] -no_script -sync -force
puts "Configured IP generated successfully."
exit 0

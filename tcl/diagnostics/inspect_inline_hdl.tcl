if {[llength $argv] < 2 || [llength $argv] % 2 != 0} {
    error "Usage: run_dir inline_name CONFIG.name value ..."
}
set run_dir [file normalize [lindex $argv 0]]
set name [lindex $argv 1]
if {$name ni {ilconcat ilslice ilconstant ilvector_logic ilreduced_logic}} {
    error "Unsupported inline HDL diagnostic: $name"
}
create_project inline_probe "$run_dir/proj" -part xc7a35tcsg324-1 -force
create_bd_design dut_0
set core [create_bd_cell -type inline_hdl -vlnv xilinx.com:inline_hdl:$name:1.0 core]
set_property -dict [lrange $argv 2 end] $core
foreach pin [get_bd_pins core/*] {
    set args [list -dir [get_property DIR $pin]]
    if {[get_property LEFT $pin] ne ""} {
        lappend args -from [get_property LEFT $pin] -to [get_property RIGHT $pin]
    }
    connect_bd_net [create_bd_port {*}$args [file tail $pin]] $pin
}
validate_bd_design
save_bd_design
generate_target all [get_files dut_0.bd]
report_property $core
puts "INLINE_PROBE_STATUS: PASS"
close_project
exit 0

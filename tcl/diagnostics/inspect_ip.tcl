set run_dir [file normalize [lindex $argv 0]]
set ip_name [lindex $argv 1]
if {$ip_name eq ""} {
    error "Usage: inspect_ip.tcl run_dir ip_name ?CONFIG.name value ...?"
}
create_project ip_probe "$run_dir/proj" -part xc7a35tcsg324-1 -force
if {[string first ":" $ip_name] >= 0} {
    create_ip -vlnv $ip_name -module_name probe_0
} else {
    create_ip -name $ip_name -vendor xilinx.com -library ip -module_name probe_0
}
set ip [get_ips probe_0]
if {[llength $argv] > 2} {
    set_property -dict [lrange $argv 2 end] $ip
}
foreach property [lsort [list_property $ip]] {
    if {[string match CONFIG.* $property]} {
        puts "IP_PROPERTY $property = [get_property $property $ip]"
    }
}
generate_target all $ip
export_ip_user_files -of_objects $ip -no_script -sync -force
puts "IP_PROBE_STATUS: PASS"
exit 0

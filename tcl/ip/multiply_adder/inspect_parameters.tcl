if {[llength $argv] != 1} {
    error "Usage: run_dir"
}
set run_dir [file normalize [lindex $argv 0]]
create_project ip_probe "$run_dir/proj" -part xc7a35tcsg324-1 -force
create_ip -name xbip_multadd -vendor xilinx.com -library ip -version 3.0 -module_name probe_0
source [file join [file dirname [info script]] metadata.tcl]
foreach row {
    {8 8 16 1 1 1 -1 -1 0}
    {8 8 16 1 1 1 0 0 0}
    {52 52 105 1 1 1 -1 -1 0}
    {25 18 48 0 0 0 -1 -1 0}
    {25 18 48 0 0 0 -1 0 1}
    {24 17 48 1 1 1 -1 -1 0}
    {24 17 47 1 1 1 -1 -1 0}
    {18 25 48 0 0 0 -1 -1 0}
    {18 25 48 0 0 0 -1 0 1}
    {17 24 47 1 1 1 -1 -1 0}
} {
    set sizes [lrange $row 0 5]
    puts "IP_LATENCY $row RESULT [::xbip_multadd_v3_0_utils::calc_multadd_latencies {*}$row artix7]"
    puts "IP_IMPLEMENTATION $sizes RESULT [::xbip_multadd_v3_0_utils::resolve_dsp48_multadd_use {*}$sizes artix7]"
}
puts "IP_HELPER_STATUS: PASS"
exit 0

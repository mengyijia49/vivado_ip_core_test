set catalog [file join $env(XILINX_VIVADO) data ip xilinx]
foreach script {
    xbip_utils_v3_0/xgui/xbip_utils_v3_0.tcl
    mult_gen_v12_0/xgui/mult_gen_v12_0_utils.tcl
    xbip_multadd_v3_0/xgui/xbip_multadd_v3_0_utils.tcl
} {
    source [file join $catalog $script]
}

proc write_multadd_metadata {run_dir ip} {
    package require json::write
    set sizes {}
    foreach key {c_a_width c_b_width c_c_width c_a_type c_b_type c_c_type} {
        lappend sizes [get_property CONFIG.$key $ip]
    }
    set ab [get_property CONFIG.c_ab_latency $ip]
    set c [get_property CONFIG.c_c_latency $ip]
    set pcin [expr {[get_property CONFIG.c_use_pcin $ip] ? 1 : 0}]
    set latencies [::xbip_multadd_v3_0_utils::calc_multadd_latencies {*}$sizes $ab $c $pcin artix7]
    set implementation [::xbip_multadd_v3_0_utils::resolve_dsp48_multadd_use {*}$sizes artix7]
    file mkdir "$run_dir/vectors"
    set fh [open "$run_dir/vectors/ip_timing.json" w]
    puts $fh [json::write object schema_version 1 ab_latency [lindex $latencies 0] \
        c_latency [lindex $latencies 1] implementation $implementation]
    close $fh
    puts "MULTADD_TIMING: ab=[lindex $latencies 0] c=[lindex $latencies 1] implementation=$implementation"
}

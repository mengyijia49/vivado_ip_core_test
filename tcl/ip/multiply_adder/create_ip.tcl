set ip_vlnv "xilinx.com:ip:xbip_multadd:3.0"
source [file join [file dirname [info script]] metadata.tcl]
set post_generate_hook write_multadd_metadata
source [file join [file dirname [info script]] .. .. shared create_configured_ip.tcl]

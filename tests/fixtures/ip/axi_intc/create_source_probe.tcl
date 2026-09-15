if {[llength $argv] != 6} {
    error "Usage: project_dir ipif_hdl ipif_library intc_hdl intc_library wrapper"
}
create_project source_probe [lindex $argv 0] -part xc7a35tcsg324-1 -force
foreach {source_path library_name} [lrange $argv 1 4] {
    if {![file isfile $source_path]} {error "Source not found: $source_path"}
    add_files -norecurse $source_path
    set_property library $library_name [get_files $source_path]
}
set wrapper [lindex $argv 5]
if {![file isfile $wrapper]} {error "Wrapper not found: $wrapper"}
add_files -norecurse $wrapper
update_compile_order -fileset sources_1
close_project
exit 0

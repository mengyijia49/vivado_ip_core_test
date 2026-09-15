if {[llength $argv] != 4} {
    error "Usage: project_dir vendor_hdl core_wrapper design_wrapper"
}
create_project source_probe [lindex $argv 0] -part xc7a35tcsg324-1 -force
foreach source_path [lrange $argv 1 end] {
    if {![file exists $source_path]} {error "Source not found: $source_path"}
    add_files -norecurse $source_path
}
update_compile_order -fileset sources_1
close_project
exit 0

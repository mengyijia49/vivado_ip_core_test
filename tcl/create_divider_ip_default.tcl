set run_dir [lindex $argv 0]

if {$run_dir eq ""} {
    puts "ERROR: run_dir argument is empty."
    exit 1
}

set part_name "xc7a35tcsg324-1"
set proj_dir "$run_dir/proj"

puts "Run dir: $run_dir"
puts "Project dir: $proj_dir"
puts "Part: $part_name"

file mkdir $run_dir

create_project divider_ip_default $proj_dir -part $part_name -force

create_ip \
    -name div_gen \
    -vendor xilinx.com \
    -library ip \
    -module_name div_gen_0

puts "===== Divider Generator CONFIG properties ====="

foreach p [lsort [list_property [get_ips div_gen_0]]] {
    if {[string match "CONFIG.*" $p]} {
        puts "$p = [get_property $p [get_ips div_gen_0]]"
    }
}

generate_target all [get_ips div_gen_0]
export_ip_user_files -of_objects [get_ips div_gen_0] -no_script -sync -force

puts "Default Divider IP generated successfully."

exit

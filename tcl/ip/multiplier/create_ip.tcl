set run_dir [lindex $argv 0]
set port_a_width [lindex $argv 1]
set port_b_width [lindex $argv 2]
set port_a_type [lindex $argv 3]
set port_b_type [lindex $argv 4]
set pipeline_stages [lindex $argv 5]

if {$run_dir eq "" || $port_a_width eq "" || $port_b_width eq "" ||
    $port_a_type eq "" || $port_b_type eq "" || $pipeline_stages eq ""} {
    puts "ERROR: 缺少 Multiplier Generator 创建参数。"
    exit 1
}

set part_name "xc7a35tcsg324-1"
set proj_dir "$run_dir/proj"
file mkdir $run_dir

puts "Run dir: $run_dir"
puts "Port A: $port_a_type $port_a_width"
puts "Port B: $port_b_type $port_b_width"
puts "Pipeline stages: $pipeline_stages"

create_project multiplier_ip_test $proj_dir -part $part_name -force
create_ip \
    -name mult_gen \
    -vendor xilinx.com \
    -library ip \
    -module_name mult_gen_0

set_property -dict [list \
    CONFIG.PortAWidth $port_a_width \
    CONFIG.PortBWidth $port_b_width \
    CONFIG.PortAType $port_a_type \
    CONFIG.PortBType $port_b_type \
    CONFIG.PipeStages $pipeline_stages \
    CONFIG.Use_Custom_Output_Width {false} \
    CONFIG.ClockEnable {false} \
    CONFIG.SyncClear {false} \
] [get_ips mult_gen_0]

puts "===== Multiplier Generator selected CONFIG properties ====="
puts "CONFIG.PortAWidth = [get_property CONFIG.PortAWidth [get_ips mult_gen_0]]"
puts "CONFIG.PortBWidth = [get_property CONFIG.PortBWidth [get_ips mult_gen_0]]"
puts "CONFIG.PortAType = [get_property CONFIG.PortAType [get_ips mult_gen_0]]"
puts "CONFIG.PortBType = [get_property CONFIG.PortBType [get_ips mult_gen_0]]"
puts "CONFIG.PipeStages = [get_property CONFIG.PipeStages [get_ips mult_gen_0]]"

generate_target all [get_ips mult_gen_0]
export_ip_user_files -of_objects [get_ips mult_gen_0] -no_script -sync -force

puts "Multiplier IP generated successfully."
exit

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

create_project divider_ip_test $proj_dir -part $part_name -force

create_ip \
    -name div_gen \
    -vendor xilinx.com \
    -library ip \
    -module_name div_gen_0

set_property -dict [list \
    CONFIG.Component_Name {div_gen_0} \
    CONFIG.dividend_and_quotient_width {16} \
    CONFIG.divisor_width {8} \
    CONFIG.remainder_type {Remainder} \
    CONFIG.operand_sign {Unsigned} \
    CONFIG.FlowControl {NonBlocking} \
] [get_ips div_gen_0]

puts "===== Divider Generator selected CONFIG properties ====="
puts "CONFIG.dividend_and_quotient_width = [get_property CONFIG.dividend_and_quotient_width [get_ips div_gen_0]]"
puts "CONFIG.divisor_width = [get_property CONFIG.divisor_width [get_ips div_gen_0]]"
puts "CONFIG.remainder_type = [get_property CONFIG.remainder_type [get_ips div_gen_0]]"
puts "CONFIG.operand_sign = [get_property CONFIG.operand_sign [get_ips div_gen_0]]"
puts "CONFIG.FlowControl = [get_property CONFIG.FlowControl [get_ips div_gen_0]]"

generate_target all [get_ips div_gen_0]
export_ip_user_files -of_objects [get_ips div_gen_0] -no_script -sync -force

puts "Divider IP generated successfully."

exit

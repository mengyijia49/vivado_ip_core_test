puts "Checking Divider Generator IP..."

set run_dir [lindex $argv 0]
if {$run_dir eq ""} {
    puts "ERROR: run_dir argument is empty."
    exit 1
}

set part_name "xc7a35tcsg324-1"

create_project ip_catalog_check "$run_dir/proj" -part $part_name -force

set div_ips [get_ipdefs -all *div_gen*]

puts "Matched IP definitions:"
puts $div_ips

if {[llength $div_ips] == 0} {
    puts "ERROR: Divider Generator IP not found."
    exit 1
}

puts "Divider Generator IP found."
exit

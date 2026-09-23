xlconcat_128_check

xc7a35tcsg324-1

dut_0

concat

![image-20260922222231050](/home/dpc/.config/Typora/typora-user-images/image-20260922222231050.png)

![image-20260922222910477](/home/dpc/.config/Typora/typora-user-images/image-20260922222910477.png)

![image-20260922222258736](/home/dpc/.config/Typora/typora-user-images/image-20260922222258736.png)

```
foreach pin [get_bd_pins core/*] {
      set name [file tail $pin]
      set args [list -dir [get_property DIR $pin]]
      set left [get_property LEFT $pin]
      if {$left ne ""} {
          lappend args -from $left -to [get_property RIGHT $pin]
      }
      set port [create_bd_port {*}$args $name]
      connect_bd_net $port $pin
  }
  validate_bd_design
  save_bd_design
```

![image-20260922223032574](/home/dpc/.config/Typora/typora-user-images/image-20260922223032574.png)

![image-20260922222341332](/home/dpc/.config/Typora/typora-user-images/image-20260922222341332.png)

![image-20260922222357115](/home/dpc/.config/Typora/typora-user-images/image-20260922222357115.png)

![image-20260922223644696](/home/dpc/.config/Typora/typora-user-images/image-20260922223644696.png)

![image-20260922223805446](/home/dpc/.config/Typora/typora-user-images/image-20260922223805446.png)
意思是：GPIO 当前设成“输入”时，我们写进去一个数；后来改成“输出”，这个数竟然被输出了。

  用你刚才的测试举例：

   步骤    操作                                 实际现象
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   1       GPIO 设为输出，写入 A5               输出 A5
────────────────────────────────
   2       GPIO 改成输入                        不再向外驱动信号
────────────────────────────────
   3       保持输入状态，向数据寄存器写入 3C    此时不会把 3C 驱动到外部
────────────────────────────────
   4       GPIO 改回输出，不再写数据            输出变成了 3C，而不是原来的 A5



  疑问就在第 3 步：输入状态下的这次写入，到底应该被忽略，还是可以提前存起来，等切回输出后使用？

  当前 issue 对手册的理解是：写入处于输入方向的位应无效。按这个理解，第 3 步不应该改变原来的输出数据，切回输出后应仍为 A5。但实测说明，3C 被保存下来了。

  你刚才的日志已经观察到：

  after_input_write=0000003C pins=3C tri=00

  其中 tri=00 表示已经切回输出，数据是 3C。

  这不是“输入状态下偷偷向外输出”，而是“输入状态下的写入被记住，切回输出后生效”。 现象已观察到；是否属于缺陷，还需要确认手册对这种写入行为的准确规定。

axi_gpio_direction_check

xc7a35tcsg324-1

AXI GPIO

dut_0

0x000000FF

![image-20260923012300746](/home/dpc/.config/Typora/typora-user-images/image-20260923012300746.png)

![image-20260923012315277](/home/dpc/.config/Typora/typora-user-images/image-20260923012315277.png)

![image-20260923012327811](/home/dpc/.config/Typora/typora-user-images/image-20260923012327811.png)

![image-20260923110751245](/home/dpc/.config/Typora/typora-user-images/image-20260923110751245.png)

![image-20260923111030448](/home/dpc/.config/Typora/typora-user-images/image-20260923111030448.png)

![image-20260923111208175](/home/dpc/.config/Typora/typora-user-images/image-20260923111208175.png)
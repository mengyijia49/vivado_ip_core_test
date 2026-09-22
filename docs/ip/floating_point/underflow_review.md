# 浮点转换下溢规则

这是参考模型的规范解释，不是已确认的 IP bug。

[PG060](https://docs.amd.com/api/khub/documents/ym1A7qsltTGP_saZFTrikQ/content)
的 UNDERFLOW 正文要求舍入后判断下溢，紧随其后的注释却要求舍入前的次正规结果归零。
当舍入进位恰好达到最小正规数时，两种解释会给出不同结果。

单精度输入 `0x387ff000` 转换到半精度时，按注释应输出零并置 UNDERFLOW；
按正文先舍入则得到 `0x0400`，不置 UNDERFLOW。
当前 Python 参考模型采用正文规则：先按目标有效位数舍入，仍过小才输出带符号的零并置 UNDERFLOW。
`reference_contract` 会记录这一选择。

这不是按 IEEE 次正规格式直接舍入。需要厂商澄清注释的适用范围；
仅凭这个文档冲突不能认定 IP 有数值缺陷。

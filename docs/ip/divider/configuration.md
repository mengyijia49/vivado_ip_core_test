# Divider 参数配置

```json
{
  "case_id": "divider_u16_u8",
  "ip_type": "divider",
  "vendor": "xilinx.com",
  "ip_name": "div_gen",
  "parameters": {
    "dividend_width": 16,
    "divisor_width": 8,
    "operand_sign": "Unsigned"
  },
  "stages": [
    "create_ip",
    "sim_demo",
    "generate_testbench",
    "sim_selfcheck"
  ],
  "verification": {
    "strategy": "directed_random",
    "strategy_version": "1.0",
    "random_seed": 20260914,
    "case_budget": 44,
    "coverage_targets": [
      "boundary_values",
      "sign_combinations",
      "nonzero_divisor"
    ]
  }
}
```

参数文件在 `configs/ip/divider/regression.json` 和 `discovery.json`。
当前要求：

- `dividend_width` 和 `divisor_width` 为正整数；
- `operand_sign` 为 `Unsigned` 或 `Signed`；
- `stages` 必须以 `create_ip` 开始；
- `sim_demo` 只在 `create_ip` 成功后执行；
- `sim_selfcheck` 前必须执行 `generate_testbench`；
- `random_seed` 固定随机序列，`case_budget` 指定总向量预算；
- 覆盖目标包括 `boundary_values`、`sign_combinations`、`nonzero_divisor`、
  `systematic_values`、`division_relations` 和 `complete_input_space`。

自检只支持字节对齐、整数商加余数、NonBlocking、无复位和无使能的配置，
生成后会核对端口位宽。除数为零和最小负数除以 -1 暂不测试。
计算方法见[数值自检](selfcheck.md)。

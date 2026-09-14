# Multiplier 参数配置

```json
{
  "case_id": "multiplier_s16_u8",
  "ip_type": "multiplier",
  "vendor": "xilinx.com",
  "ip_name": "mult_gen",
  "parameters": {
    "a_width": 16,
    "b_width": 8,
    "a_type": "Signed",
    "b_type": "Unsigned",
    "pipeline_stages": 3
  },
  "stages": [
    "create_ip",
    "generate_testbench",
    "sim_selfcheck"
  ],
  "verification": {
    "strategy": "directed_random",
    "strategy_version": "1.0",
    "random_seed": 20260918,
    "case_budget": 45,
    "coverage_targets": [
      "boundary_values",
      "sign_combinations",
      "full_precision"
    ]
  }
}
```

参数文件在 `configs/ip/multiplier/regression.json` 和 `discovery.json`。
当前要求：

- `a_width` 和 `b_width` 为 2 到 64 的整数；
- `a_type` 和 `b_type` 分别为 `Unsigned` 或 `Signed`；
- `pipeline_stages` 为 1 到 64 的整数；
- 使用完整精度输出，不启用时钟使能和同步清零；
- Vivado 2025.2 的该 IP 不生成官方 demo testbench，因此不允许配置
  `sim_demo` 阶段；
- 覆盖目标只能使用 `boundary_values`、`sign_combinations`、
  `full_precision`、`operand_magnitude`、`systematic_values` 和 `complete_input_space`。
  含义见[测试生成策略](../../test_generation_strategies.md)。

探索配置还包括两路有符号、反向混合符号、不等位宽和不同流水线深度。
使能、复位、截位、舍入和常量乘法暂不测试，采样方法见[数值自检](selfcheck.md)。

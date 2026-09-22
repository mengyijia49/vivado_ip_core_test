# 公开证据归档

`runs/` 和 `reports/` 太大，不适合直接提交到仓库。本目录复制问题记录实际引用的文件，
同学克隆仓库后不需要访问原作者电脑，也能查看 2026.1 的报告、关键观察和日志。

- 2026.1 运行报告、独立复现摘要、失败摘要、关键输入输出和日志。
- 独立 VHDL testbench 在仓库的 `tests/fixtures/` 下；完整 Vivado 工程不提交。
- `manifest.json` 记录来源文件、哈希和导出方式。
- `SHA256SUMS` 可校验公开副本有没有被改动。

Vivado 2026.1 的[问题观察](vivado_2026_1/observations/)保存报告、观察值和日志。
478 组常用配置的报告、适配复测和新差异的输入输出在
[全量运行证据](vivado_2026_1/full_regression/)。
它们都不是厂商确认结果，也不表示硬件实现一定有同样问题。

重新导出和校验：

```bash
python3 scripts/evidence/archive.py --export
python3 scripts/evidence/archive.py --verify
```

如果本机仍保留原始 `runs/` 和 `reports/`，可以检查公开副本是否仍与原始文件一致：

```bash
python3 scripts/evidence/archive.py --verify --check-sources
```

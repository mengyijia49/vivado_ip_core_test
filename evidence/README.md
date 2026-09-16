# 完整证据包

`runs/` 和 `reports/` 太大，不适合直接提交到仓库。本目录复制问题记录实际引用的文件，
同学克隆仓库后不需要访问原作者电脑，也能查看首次运行、独立复现、报告和日志。

- 首次运行和独立复现的原始观察、失败摘要、输入输出和日志。
- 独立复现用的 VHDL testbench。
- XCI 中提取出的参数摘要。完整 Vivado 工程体积过大，不提交缓存和预编译库。
- `manifest.json` 记录来源文件、哈希和导出方式。
- `SHA256SUMS` 可校验公开副本有没有被改动。

这些证据只说明“本机 Vivado 2025.2 行为仿真出现了这些现象”。它们不是厂商确认结果，也不表示硬件实现一定有同样问题。

重新导出和校验：

```bash
python3 scripts/evidence/archive.py --export
python3 scripts/evidence/archive.py --verify
```

如果本机仍保留原始 `runs/` 和 `reports/`，可以检查公开副本是否仍与原始文件一致：

```bash
python3 scripts/evidence/archive.py --verify --check-sources
```

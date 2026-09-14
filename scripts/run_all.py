#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run() -> int:
    src_dir = ROOT / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from vivado_ip_test.application.main import main

    return main(ROOT)


if __name__ == "__main__":
    raise SystemExit(run())

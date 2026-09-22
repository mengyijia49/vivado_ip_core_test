import re
import shutil
import subprocess


def detect_vivado_version() -> str:
    executable = shutil.which("vivado")
    if executable is None:
        return "unavailable"
    try:
        result = subprocess.run([executable, "-version"], capture_output=True,
                                text=True, timeout=15, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError(f"无法读取 Vivado 版本：{exc}") from exc
    match = re.search(r"^vivado v(\d{4}\.\d+(?:\.\d+)?)\b", result.stdout, re.MULTILINE)
    if match is None:
        raise ValueError("Vivado -version 未返回可识别的版本号")
    return match.group(1)

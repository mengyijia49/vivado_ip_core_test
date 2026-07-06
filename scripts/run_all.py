#!/usr/bin/env python3
import csv
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"
REPORTS_DIR = ROOT / "reports"
LOG_DIR = RUNS_DIR / "logs"

REPORT_PATH = REPORTS_DIR / "report.csv"

CREATE_DIVIDER_TCL = ROOT / "tcl" / "create_divider_ip.tcl"


def run_cmd(cmd, cwd, timeout_sec):
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_sec,
        )
        return result.returncode, result.stdout, "OK"
    except subprocess.TimeoutExpired as e:
        output = e.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="ignore")
        return 124, output, "TIMEOUT"


def write_report(rows):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with REPORT_PATH.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "case_id",
            "stage",
            "status",
            "run_dir",
            "log_path",
        ])
        writer.writerows(rows)


def run_divider_create():
    case_id = "divider_u16_u8"
    run_dir = RUNS_DIR / case_id
    log_path = LOG_DIR / f"{case_id}_create.log"
    jou_path = LOG_DIR / f"{case_id}_create.jou"

    vivado = shutil.which("vivado")
    if vivado is None:
        return [
            case_id,
            "create_ip",
            "VIVADO_NOT_FOUND",
            str(run_dir),
            str(log_path),
        ]

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        vivado,
        "-mode", "batch",
        "-journal", str(jou_path),
        "-log", str(log_path),
        "-source", str(CREATE_DIVIDER_TCL),
        "-tclargs", str(run_dir),
    ]

    print("Running Divider IP creation:")
    print(" ".join(cmd))

    code, output, reason = run_cmd(cmd, cwd=ROOT, timeout_sec=600)
    print(output)

    if reason == "TIMEOUT":
        return [
            case_id,
            "create_ip",
            "TIMEOUT",
            str(run_dir),
            str(log_path),
        ]

    if code != 0:
        return [
            case_id,
            "create_ip",
            "CREATE_IP_FAILED",
            str(run_dir),
            str(log_path),
        ]

    if not log_path.exists():
        return [
            case_id,
            "create_ip",
            "LOG_NOT_FOUND",
            str(run_dir),
            str(log_path),
        ]

    log_text = log_path.read_text(errors="ignore")

    if "Divider IP generated successfully." not in log_text:
        return [
            case_id,
            "create_ip",
            "LOG_CHECK_FAILED",
            str(run_dir),
            str(log_path),
        ]

    xci_files = list(run_dir.rglob("div_gen_0.xci"))
    if not xci_files:
        return [
            case_id,
            "create_ip",
            "XCI_NOT_FOUND",
            str(run_dir),
            str(log_path),
        ]

    return [
        case_id,
        "create_ip",
        "PASS",
        str(run_dir),
        str(log_path),
    ]


def main():
    row = run_divider_create()
    write_report([row])

    print("\nReport written to:")
    print(REPORT_PATH)

    print("\nResult:")
    print(",".join(row))

    return 0 if row[2] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

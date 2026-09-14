#!/usr/bin/env python3
import csv
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"
REPORTS_DIR = ROOT / "reports"

TCL_SCRIPT = ROOT / "tcl" / "smoke_test.tcl"
LOG_PATH = RUNS_DIR / "smoke_from_python.log"
JOU_PATH = RUNS_DIR / "smoke_from_python.jou"
REPORT_PATH = REPORTS_DIR / "report.csv"


def main():
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    vivado = shutil.which("vivado")
    if vivado is None:
        write_report("smoke", "batch_tcl", "VIVADO_NOT_FOUND", str(LOG_PATH))
        print("ERROR: vivado command not found. Please source Vivado settings64.sh first.")
        return 1

    cmd = [
        vivado,
        "-mode", "batch",
        "-source", str(TCL_SCRIPT),
        "-journal", str(JOU_PATH),
        "-log", str(LOG_PATH),
    ]

    print("Running command:")
    print(" ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        write_report("smoke", "batch_tcl", "TIMEOUT", str(LOG_PATH))
        print("ERROR: Vivado timeout.")
        return 1

    print(result.stdout)

    if result.returncode != 0:
        write_report("smoke", "batch_tcl", "FAILED", str(LOG_PATH))
        print("ERROR: Vivado returned non-zero exit code.")
        return result.returncode

    log_text = LOG_PATH.read_text(errors="ignore")
    if "Vivado batch mode OK" in log_text:
        write_report("smoke", "batch_tcl", "PASS", str(LOG_PATH))
        print("PASS: Python successfully called Vivado batch Tcl.")
        return 0
    else:
        write_report("smoke", "batch_tcl", "LOG_CHECK_FAILED", str(LOG_PATH))
        print("ERROR: Vivado ran, but expected message was not found in log.")
        return 1


def write_report(case_id, stage, status, log_path):
    with REPORT_PATH.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "stage", "status", "log_path"])
        writer.writerow([case_id, stage, status, log_path])


if __name__ == "__main__":
    raise SystemExit(main())

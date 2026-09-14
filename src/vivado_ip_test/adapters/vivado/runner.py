import json
import shlex
import shutil
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Sequence

from vivado_ip_test.infrastructure import CommandResult, CommandRunner


class VivadoBatchRunner:
    def __init__(self, command_runner: CommandRunner, root: Path) -> None:
        self._command_runner = command_runner
        self._root = root

    @property
    def executable(self) -> str | None:
        return shutil.which("vivado")

    def run(
        self,
        *,
        description: str,
        source: Path,
        tclargs: Sequence[str],
        journal_path: Path,
        log_path: Path,
        timeout_sec: int = 600,
        work_dir: Path | None = None,
    ) -> CommandResult | None:
        cwd = (work_dir or self._root).resolve()
        cwd.mkdir(parents=True, exist_ok=True)
        process_log = log_path.with_suffix(".process.log")
        invocation_path = log_path.with_suffix(".invocation.json")
        for path in (log_path, journal_path, process_log, invocation_path):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.unlink(missing_ok=True)

        executable = self.executable
        command = [
            executable or "vivado",
            "-mode",
            "batch",
            "-journal",
            str(journal_path),
            "-log",
            str(log_path),
            "-source",
            str(source),
            "-tclargs",
            *tclargs,
        ]

        invocation = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "command": command,
            "cwd": str(cwd),
            "timeout_seconds": timeout_sec,
            "state": "running",
        }
        self._write_invocation(invocation_path, invocation)
        started = perf_counter()
        output = ""
        print(description, flush=True)
        print(shlex.join(command), flush=True)
        try:
            if executable is None:
                output = "VIVADO_NOT_FOUND: PATH 中找不到 vivado\n"
                invocation.update(state="unavailable", returncode=None, timed_out=False)
                return None
            try:
                result = self._command_runner.run(command, cwd, timeout_sec)
            except OSError as exc:
                result = CommandResult(
                    127, f"无法启动 Vivado：{exc}\n",
                    elapsed_seconds=perf_counter() - started,
                )
            output = result.output
            invocation.update(state="finished", **result.metrics())
            return result
        except BaseException as exc:
            output = f"{type(exc).__name__}: {exc}\n"
            invocation.update(state="interrupted", exception=output.strip())
            raise
        finally:
            process_log.write_text(output)
            invocation.update(
                finished_at=datetime.now(timezone.utc).isoformat(),
                elapsed_seconds=perf_counter() - started,
            )
            self._write_invocation(invocation_path, invocation)
            print(output, flush=True)

    @staticmethod
    def _write_invocation(path: Path, metadata: dict[str, object]) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
        temporary.replace(path)

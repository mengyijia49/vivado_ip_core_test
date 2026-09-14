import os
import signal
import subprocess
from time import perf_counter
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    output: str
    timed_out: bool = False
    elapsed_seconds: float = 0.0

    def metrics(self) -> dict[str, object]:
        return {
            "returncode": self.returncode,
            "timed_out": self.timed_out,
            "elapsed_seconds": self.elapsed_seconds,
        }


class CommandRunner:
    def run(
        self,
        command: Sequence[str],
        cwd: Path,
        timeout_sec: int,
    ) -> CommandResult:
        started = perf_counter()
        with subprocess.Popen(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            errors="replace",
            start_new_session=True,
        ) as process:
            try:
                output, _ = process.communicate(timeout=timeout_sec)
                return CommandResult(
                    process.returncode, output,
                    elapsed_seconds=perf_counter() - started,
                )
            except subprocess.TimeoutExpired:
                self._kill_group(process.pid)
                output, _ = process.communicate()
                return CommandResult(
                    124, output, timed_out=True,
                    elapsed_seconds=perf_counter() - started,
                )
            except BaseException:
                self._kill_group(process.pid)
                process.communicate()
                raise

    @staticmethod
    def _kill_group(pid: int) -> None:
        # Vivado 经多层 shell 启动 XSim，只终止直接子进程会留下仿真进程。
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

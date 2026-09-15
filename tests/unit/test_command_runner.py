from pathlib import Path
import sys
import tempfile
import time
import unittest

from vivado_ip_test.infrastructure import CommandRunner


@unittest.skipUnless(sys.platform == "linux", "Vivado 执行器面向 Linux")
class CommandRunnerTests(unittest.TestCase):
    def test_collects_both_streams_and_preserves_exit_code(self):
        result = CommandRunner().run(
            [sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr); sys.exit(7)"],
            Path.cwd(),
            5,
        )
        self.assertEqual(result.returncode, 7)
        self.assertIn("out", result.output)
        self.assertIn("err", result.output)
        self.assertFalse(result.timed_out)

    def test_timeout_kills_grandchild_holding_output_pipe(self):
        child = "import time; time.sleep(60)"
        parent = (
            "import subprocess, sys, time; "
            f"child = subprocess.Popen([sys.executable, '-c', {child!r}]); "
            "print(child.pid, flush=True); time.sleep(60)"
        )
        with tempfile.TemporaryDirectory() as directory:
            started = time.monotonic()
            result = CommandRunner().run(
                [sys.executable, "-c", parent], Path(directory), 1
            )
        self.assertTrue(result.timed_out)
        self.assertEqual(result.returncode, 124)
        self.assertLess(time.monotonic() - started, 10)
        pid = int(result.output.strip())
        # 已退出的孤儿进程可能短暂等待 init 回收。
        for _ in range(100):
            try:
                state = Path(f"/proc/{pid}/stat").read_text().split()[2]
            except (FileNotFoundError, ProcessLookupError):
                return
            if state == "Z":
                return
            time.sleep(0.01)
        self.fail(f"超时后仍有子进程存活：{pid}")

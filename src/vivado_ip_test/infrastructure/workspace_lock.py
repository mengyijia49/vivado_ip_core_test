import fcntl
from contextlib import contextmanager
from pathlib import Path


class WorkspaceBusy(RuntimeError):
    pass


@contextmanager
def workspace_lock(runs_dir: Path):
    runs_dir.mkdir(parents=True, exist_ok=True)
    # 保留锁文件的 inode，避免释放与另一个进程重新打开之间的竞争。
    with (runs_dir / ".pipeline.lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise WorkspaceBusy("此工作目录已有测试任务运行，请等待完成或使用其他工作目录") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)

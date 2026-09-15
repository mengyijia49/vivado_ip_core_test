"""精确去重：少量键留在内存，大集合转入可丢弃的临时索引。"""

from datetime import datetime
import sqlite3
from tempfile import TemporaryDirectory


class UniqueKeys:
    def __init__(self, memory_limit=8192):
        if type(memory_limit) is not int or memory_limit < 0:
            raise ValueError("memory_limit must be a nonnegative integer")
        self._limit = memory_limit
        self._keys = set()
        self._directory = None
        self._database = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self._database is not None:
            self._database.close()
            self._database = None
        if self._directory is not None:
            self._directory.cleanup()
            self._directory = None
        self._keys.clear()

    def add(self, key: str) -> bool:
        if not isinstance(key, str):
            raise TypeError("unique keys must be strings")
        if self._database is None:
            if key in self._keys:
                return False
            if len(self._keys) < self._limit:
                self._keys.add(key)
                return True
            self._spill()
        try:
            self._database.execute("INSERT INTO keys(value) VALUES (?)", (key,))
        except sqlite3.IntegrityError:
            return False
        return True

    def _spill(self):
        stamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S_UTC%z")
        self._directory = TemporaryDirectory(prefix=f"vivado-config-{stamp}-")
        try:
            self._database = sqlite3.connect(self._directory.name + "/keys.sqlite")
            # 保留语句回滚；索引退出即删，不承担崩溃后的恢复或持久化。
            self._database.execute("PRAGMA journal_mode=MEMORY")
            self._database.execute("PRAGMA synchronous=OFF")
            self._database.execute("PRAGMA cache_size=-2048")
            self._database.execute("CREATE TABLE keys(value TEXT PRIMARY KEY) WITHOUT ROWID")
            self._database.executemany("INSERT INTO keys(value) VALUES (?)", ((k,) for k in self._keys))
            self._keys.clear()
        except BaseException:
            self.close()
            raise

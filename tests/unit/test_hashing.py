import hashlib
import tempfile
import unittest
from pathlib import Path

from vivado_ip_test.infrastructure import sha256_file


class HashingTests(unittest.TestCase):
    def test_hashes_file_bytes_with_sha256(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "artifact.bin"
            path.write_bytes(b"reproducible artifact\n")

            actual = sha256_file(path)

        expected = hashlib.sha256(b"reproducible artifact\n").hexdigest()
        self.assertEqual(actual, expected)

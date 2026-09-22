import subprocess
import unittest
from unittest.mock import patch

from vivado_ip_test.infrastructure.vivado_version import detect_vivado_version


class VivadoVersionTests(unittest.TestCase):
    def test_detects_release_and_patch_versions(self):
        for version in ("2026.0", "2026.1", "2026.1.1"):
            with self.subTest(version=version), patch(
                "vivado_ip_test.infrastructure.vivado_version.shutil.which", return_value="/opt/vivado"
            ), patch("vivado_ip_test.infrastructure.vivado_version.subprocess.run",
                     return_value=subprocess.CompletedProcess([], 0, f"vivado v{version} (64-bit)\n", "")):
                self.assertEqual(detect_vivado_version(), version)

    def test_missing_tool_uses_separate_unavailable_directory(self):
        with patch("vivado_ip_test.infrastructure.vivado_version.shutil.which", return_value=None):
            self.assertEqual(detect_vivado_version(), "unavailable")

    def test_unknown_output_is_rejected(self):
        with patch("vivado_ip_test.infrastructure.vivado_version.shutil.which", return_value="/opt/vivado"), \
             patch("vivado_ip_test.infrastructure.vivado_version.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 0, "unexpected", "")):
            with self.assertRaisesRegex(ValueError, "版本号"):
                detect_vivado_version()

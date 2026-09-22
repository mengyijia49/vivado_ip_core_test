"""通用基础设施。"""

from .command import CommandResult, CommandRunner
from .hashing import sha256_file
from .layout import RepositoryLayout
from .output import output_fields_within_tolerance, output_files_match
from .vivado_version import detect_vivado_version

__all__ = [
    "CommandResult",
    "CommandRunner",
    "RepositoryLayout",
    "output_files_match",
    "output_fields_within_tolerance",
    "sha256_file",
    "detect_vivado_version",
]

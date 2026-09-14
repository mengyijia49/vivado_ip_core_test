"""通用基础设施。"""

from .command import CommandResult, CommandRunner
from .hashing import sha256_file
from .layout import RepositoryLayout
from .output import output_files_match

__all__ = [
    "CommandResult",
    "CommandRunner",
    "RepositoryLayout",
    "output_files_match",
    "sha256_file",
]

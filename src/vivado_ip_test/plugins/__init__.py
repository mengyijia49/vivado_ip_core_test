"""IP 类型插件。"""

from .base import IpPlugin, PluginError
from .registry import PluginRegistry

__all__ = ["IpPlugin", "PluginError", "PluginRegistry"]

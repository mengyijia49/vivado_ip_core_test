from vivado_ip_test.plugins.base import IpPlugin, PluginError


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, IpPlugin] = {}

    def register(self, plugin: IpPlugin) -> None:
        if plugin.ip_type in self._plugins:
            raise PluginError(f"IP 插件重复注册：{plugin.ip_type}")
        self._plugins[plugin.ip_type] = plugin

    def resolve(self, ip_type: str) -> IpPlugin:
        try:
            return self._plugins[ip_type]
        except KeyError as exc:
            raise PluginError(f"不支持的 IP 类型：{ip_type}") from exc

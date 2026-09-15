from pathlib import Path

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.infrastructure import RepositoryLayout
from vivado_ip_test.plugins.catalog import create_plugin_registry
from vivado_ip_test.strategies import create_default_strategy_registry


ROOT = Path(__file__).resolve().parents[3]


def plugin_case(ip_type, root=None):
    case = load_test_cases(ROOT / f"configs/ip/{ip_type}/regression.json")[0]
    registry = create_plugin_registry(RepositoryLayout(root or ROOT), create_default_strategy_registry())
    return registry.resolve(ip_type), case

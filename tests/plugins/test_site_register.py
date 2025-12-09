import importlib
import inspect
from pathlib import Path

import pytest

from novelkit.plugins import registry

SITES_DIR = Path(__file__).parents[2] / "src" / "novelkit" / "plugins" / "sites"

MODULE_DECORATOR_MAP = {
    "fetcher": "_fetchers",
    "parser": "_parsers",
    "client": "_client",
}


@pytest.mark.parametrize("site_path", [p for p in SITES_DIR.iterdir() if p.is_dir()])
def test_site_plugin_structure(site_path: Path):
    site_key = site_path.name  # directory name
    normalized_key = registry.hub._normalize_key(site_key)

    for mod_name, registry_attr in MODULE_DECORATOR_MAP.items():
        py_file = site_path / f"{mod_name}.py"
        if not py_file.exists():
            continue  # Optional module; skip

        module_path = f"novelkit.plugins.sites.{site_key}.{mod_name}"
        module = importlib.import_module(module_path)

        # All classes defined in this module
        classes = {
            name: cls
            for name, cls in inspect.getmembers(module, inspect.isclass)
            if cls.__module__ == module_path
        }

        assert classes, f"{module_path} contains no classes"

        reg_dict = getattr(registry.hub, registry_attr)
        assert isinstance(reg_dict, dict)

        registered_cls = reg_dict.get(normalized_key)
        assert registered_cls is not None, (
            f"{mod_name}: site '{site_key}' was not registered in hub.{registry_attr}"
        )

        cls_site_key = getattr(registered_cls, "site_key", None)
        assert cls_site_key is not None, (
            f"{registered_cls.__name__} must define a site_key attribute"
        )
        assert cls_site_key == site_key, (
            f"{registered_cls.__name__}.site_key = {cls_site_key!r} "
            f"does not match directory name '{site_key}'"
        )

        assert registered_cls.__module__ == module_path, (
            f"Registered {registered_cls.__name__} not defined in {module_path}"
        )

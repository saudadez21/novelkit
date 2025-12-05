import pkgutil

import novelkit.infra.sessions as sessions_pkg

from .utils import SUPPORTED_BACKENDS


def test_backend_autodiscovery():
    """Ensure SUPPORTED_BACKENDS matches available _*.py modules."""
    discovered = {
        modinfo.name[1:]
        for modinfo in pkgutil.iter_modules(sessions_pkg.__path__)
        if modinfo.name.startswith("_")
    }
    assert discovered <= SUPPORTED_BACKENDS

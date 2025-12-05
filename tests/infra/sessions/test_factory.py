import pytest

from novelkit.infra.sessions import create_session
from novelkit.infra.sessions.base import BaseSession
from novelkit.schemas import SessionConfig

from .utils import SUPPORTED_BACKENDS, safe_create


def test_factory_rejects_unknown_backend():
    with pytest.raises(ValueError):
        create_session("not-a-backend", SessionConfig())


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
def test_factory_supports_declared_backends(backend):
    cfg = SessionConfig()
    s = safe_create(backend, cfg)
    assert isinstance(s, BaseSession)

from novelkit.infra.http_defaults import DEFAULT_HEADERS
from novelkit.plugins.base.client import BaseClient
from novelkit.plugins.registry import hub


@hub.register_client()
class B520Client(BaseClient):
    site_key = "b520"
    r18 = False
    support_search = True

    MEDIA_BASE_HEADERS = {
        **DEFAULT_HEADERS,
        "Referer": "http://www.b520.cc/",
    }

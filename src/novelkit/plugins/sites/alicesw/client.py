from novelkit.plugins.base.client import BaseClient
from novelkit.plugins.registry import hub


@hub.register_client()
class AliceswClient(BaseClient):
    site_key = "alicesw"
    r18 = True
    support_search = True

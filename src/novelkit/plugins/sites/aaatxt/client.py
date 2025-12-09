from novelkit.plugins.base.client import BaseClient
from novelkit.plugins.registry import hub


@hub.register_client()
class AaatxtClient(BaseClient):
    site_key = "aaatxt"
    r18 = True
    support_search = False

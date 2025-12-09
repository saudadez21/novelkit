# Registry

The registry provides a unified system for discovering and loading
site-specific plugin components.

It manages four categories of plugins:

- fetchers
- parsers
- clients
- processors

Each plugin is registered under a site key or name and later instantiated
through helper methods such as `hub.build_client()`.

---

::: novelkit.plugins.registry.PluginHub

---

## Registering Plugins

All plugin components are typically registered using decorators.

A plugin module is usually located under:

```
novelkit.plugins.sites.<site_key>.<kind>
```

Example: `novelkit.plugins.sites.mysite.fetcher`.

### Fetcher

```py
from novelkit.plugins.base.fetcher import GenericFetcher
from novelkit.plugins.registry import hub

@hub.register_fetcher()
class MySiteFetcher(GenericFetcher):
    site_key = "mysite"
    BASE_URL = "https://example.com"

    BOOK_INFO_PATH = "/book/{book_id}.html"
    CHAPTER_PATH   = "/chapter/{chapter_id}.html"
```

### Parser

```py
from lxml import html
from novelkit.plugins.base.parser import BaseParser
from novelkit.plugins.registry import hub

@hub.register_parser()
class MySiteParser(BaseParser):
    site_key = "mysite"
    site_name = "My Novel Site"
    BASE_URL = "https://example.com"

    def parse_book_info(self, raw_pages, book_id, **_):
        tree = html.fromstring(raw_pages[0])
        ...
```

### Client

Most sites do not need a custom client, but it is possible to override
hooks (e.g., export formatting):

```py
from novelkit.plugins.base.client import BaseClient
from novelkit.plugins.registry import hub
from novelkit.schemas import ChapterDict

@hub.register_client()
class MySiteClient(BaseClient):
    site_key = "mysite"
    site_name = "My Novel Site"

    def _xp_txt_chapter_footer(self, chap: ChapterDict) -> str:
        return chap["extra"].get("author_say", "")
```

### Processor

```py
from novelkit.plugins.registry import hub

@hub.register_processor("clean_text")
class CleanTextProcessor:
    def __init__(self, config):
        self.remove_ads = config.get("remove_ads", False)

    def process_chapter(self, chapter):
        ...
        return chapter
```

---

## Creating Plugin Instances

The registry resolves plugin classes using the site key.

**Build a fetcher**

```py
fetcher = hub.build_fetcher("mysite")
```

**Build a parser**

```py
parser = hub.build_parser("mysite")
```

**Build a client**

This produces either a custom client (if registered)
or a generic default client:

```py
client = hub.build_client("mysite")
```

**Build a processor**

```py
processor = hub.build_processor("clean_text", {"remove_ads": True})
```

---

## Enabling Local Plugins

You can load user-defined plugins by enabling an additional namespace:

```py
hub.enable_local_plugins("./my_plugins", override=True)
```

This allows plugins under:

```
./my_plugins/novel_plugins/sites/<site_key>/
```

to participate in discovery and registration.

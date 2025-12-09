# Fetcher

A **Fetcher** is responsible for performing all network operations required
to interact with a novel platform.

It encapsulates:

- Session creation and HTTP handling
- Authentication (login/logout)
- Rate limiting
- Fetching book metadata, chapters, search results
- Utility helpers (binary/text fetching, URL utilities, etc)

---

::: novelkit.plugins.protocols.fetcher.FetcherProtocol

---

## BaseFetcher

`BaseFetcher` provides:

- Shared HTTP session handling
- Login and cookie injection helpers
- Built-in rate limiting via token bucket
- Fetch utilities (`fetch_text`, `fetch_binary`)
- Optional search support (default = unsupported)
- State persistence (`load_state` / `save_state`)
- Async context manager (`async with fetcher:`)

---

## GenericFetcher

`GenericFetcher` implements a flexible, declarative pattern for sites that share
a similar page layout:

- One or more "book info" pages
- Optional separate catalog
- One or more paginated chapter pages
- Optional ID transformation rules
- Optional locale-based base URL selection

Most real sites can be implemented simply by subclassing `GenericFetcher` and
defining:

- `BASE_URL`
- Path templates like `BOOK_INFO_PATH`, `CHAPTER_PATH`
- Pagination functions such as `relative_chapter_url()`
- Replacement rules like `BOOK_ID_REPLACEMENTS`

---

## Examples: Implementing Custom Fetchers

This section provides real, production-grade examples of building
fetchers for different types of novel sites.

Fetchers can be implemented in two main ways:

1. **Subclassing `BaseFetcher`**: Full manual control over URLs, headers, encoding, etc.
2. **Subclassing `GenericFetcher`**: Use configurable patterns for common site structures.

---

### 1. Subclassing `BaseFetcher`

Use `BaseFetcher` when the site does **not** follow a predictable pattern
or when you want full control over URL construction, headers, or encoding.

```py
from typing import Any
from novelkit.plugins.base.fetcher import BaseFetcher
from novelkit.plugins.registry import hub

@hub.register_fetcher()
class B520Fetcher(BaseFetcher):
    site_key = "b520"
    site_name = "笔趣阁"
    BASE_URL = "http://www.b520.cc"

    BOOK_INFO_URL = "http://www.b520.cc/{book_id}/"
    CHAPTER_URL   = "http://www.b520.cc/{book_id}/{chapter_id}.html"

    async def fetch_book_info(
        self,
        book_id: str,
        **kwargs: Any,
    ) -> list[str]:
        url = self.BOOK_INFO_URL.format(book_id=book_id)
        return [
            await self.fetch(
                url,
                headers={"Referer": "http://www.b520.cc/"},
            )
        ]

    async def fetch_chapter_content(
        self,
        chapter_id: str,
        book_id: str | None = None,
        **kwargs: Any,
    ) -> list[str]:
        if not book_id:
            raise ValueError(f"{self.site_key}: book_id is required")
        url = self.CHAPTER_URL.format(book_id=book_id, chapter_id=chapter_id)
        return [
            await self.fetch(
                url,
                headers={"Referer": "http://www.b520.cc/"},
                encoding="gbk",
            )
        ]
```

This approach is best for sites with unique behaviors, special encoding
or per-request headers.

---

### 2. Simple Single-Page Site: `GenericFetcher`

```py
import logging
from typing import Any

from novelkit.plugins.base.fetcher import GenericFetcher
from novelkit.plugins.registry import hub

logger = logging.getLogger(__name__)

@hub.register_fetcher()
class AaatxtFetcher(GenericFetcher):
    site_key = "aaatxt"
    site_name = "3A电子书"
    BASE_URL = "http://www.aaatxt.com"

    BOOK_INFO_PATH = "/shu/{book_id}.html"
    CHAPTER_PATH   = "/yuedu/{book_id}_{chapter_id}.html"

    SEARCH_URL = "http://www.aaatxt.com/search.php"

    async def fetch_search_result(
        self,
        keyword: str,
        **kwargs: Any,
    ) -> list[str]:
        # site uses gb2312 encoding for search parameters
        params = {
            "keyword": self._quote(keyword, encoding="gb2312", errors="replace"),
            "submit": self._quote("搜 索", encoding="gb2312", errors="replace"),
        }

        full_url = self._build_url(self.SEARCH_URL, params)

        headers = {
            **self.session.headers,
            "Host": "www.aaatxt.com",
            "Referer": "http://www.aaatxt.com/",
        }

        resp = await self.session.get(full_url, headers=headers)
        if not resp.ok:
            logger.info("Failed to fetch search from %s", self.SEARCH_URL)
            return []

        return [resp.text]
```

`GenericFetcher` handles:

* building URLs using BOOK_INFO_PATH / CHAPTER_PATH
* joining with BASE_URL
* calling `fetch_text()` internally

---

### 3. Pagination Example: Multi-Page Info or Chapter Content

Some sites split information or chapters across multiple pages, like:

```
/{book_id}/index.html
/{book_id}/index_2.html
/{book_id}/{chapter_id}.html
/{book_id}/{chapter_id}_2.html
```

Here's how to support this:

```py
from novelkit.plugins.base.fetcher import GenericFetcher
from novelkit.plugins.registry import hub

@hub.register_fetcher()
class Biquge5Fetcher(GenericFetcher):
    site_key = "biquge5"
    site_name = "笔趣阁"
    BASE_URL = "https://www.biquge5.com"

    USE_PAGINATED_INFO = True
    USE_PAGINATED_CHAPTER = True

    @classmethod
    def relative_info_url(cls, book_id: str, idx: int) -> str:
        return (
            f"/{book_id}/index_{idx}.html"
            if idx > 1 else f"/{book_id}/"
        )

    @classmethod
    def relative_chapter_url(cls, book_id: str | None, chapter_id: str, idx: int) -> str:
        if not book_id:
            raise ValueError("book_id is required")
        return (
            f"/{book_id}/{chapter_id}_{idx}.html"
            if idx > 1 else f"/{book_id}/{chapter_id}.html"
        )
```

`GenericFetcher` will:

* automatically generate paginated URLs
* stop when `should_continue_pagination()` returns False
* merge all pages into the returned list

---

### 4. Separate Info & Catalog Pages

Some sites store book information and the catalog (table of contents) on
different pages, often using unrelated URL patterns.

`GenericFetcher` supports this via:

```py
from novelkit.plugins.base.fetcher import GenericFetcher
from novelkit.plugins.registry import hub

@hub.register_fetcher()
class I25zwFetcher(GenericFetcher):
    site_key = "i25zw"
    site_name = "25中文网"
    BASE_URL = "https://www.i25zw.com"

    HAS_SEPARATE_CATALOG = True

    BOOK_INFO_PATH    = "/book/{book_id}.html"
    BOOK_CATALOG_PATH = "/{book_id}/"
    CHAPTER_PATH      = "/{book_id}/{chapter_id}.html"
```

`GenericFetcher.fetch_book_info` will automatically:

* fetch book info page
* then fetch catalog page
* merge into a single list

---

## Initialization & Lifecycle

Fetchers must be initialized before use:

```py
from novelkit.plugins.registry import hub

async with hub.build_fetcher("my_site") as fetcher:
    pages = await fetcher.fetch_book_info("12345")
```

Initialization steps include:

* Setting up the underlying HTTP session
* Applying rate-limit settings
* Restoring persistent authentication state

Cleanup (`close()`) closes the session and releases resources.

---

## Authentication

`BaseFetcher.login()` supports simple cookie-based login:

```py
await fetcher.login(cookies={"session": "abcd"})
```

Sites requiring more complex flows should override:

* `login()`
* `check_login_status()`
* `logout()`

The fetcher exposes `is_logged_in` and `login_fields` to support interactive UIs.

---

## Error Handling

Fetch operations may raise:

* `ConnectionError` -> network failure, bad status codes
* `RuntimeError` -> fetcher not initialized
* `NotImplementedError` -> site does not support search or required methods

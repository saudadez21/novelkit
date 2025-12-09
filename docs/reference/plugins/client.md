# Client

A **Client** represents the high-level interface for interacting with a
novel site. It provides access to metadata retrieval, chapter downloading,
optional processing, and exporting.

Most sites do **not** require a custom client implementation.

A client is only needed when you want to customize behavior: for example,
adding additional export formatting or overriding helper hooks.

---

::: novelkit.plugins.protocols.client.ClientProtocol

---

## Example: Custom Client With Hooks

Site-specific clients typically extend `BaseClient` only to override
certain behaviors. For example, customizing TXT export:

```py
from novelkit.plugins.base.client import BaseClient
from novelkit.plugins.registry import hub
from novelkit.schemas import ChapterDict

@hub.register_client()
class MySiteClient(BaseClient):
    site_key = "mysite"
    site_name = "My Novel Site"

    def _xp_txt_chapter_footer(self, chap: ChapterDict) -> str:
        """Append a footer to each exported chapter."""
        msg = chap["extra"].get("author_say")
        return f"作者说：{msg}" if msg else ""
```

---

## Example: Using a Client

```py
import asyncio
from novelkit.plugins.registry import hub

async def main():
    client = hub.build_client("mysite")

    async with client:
        info = await client.get_book_info("12345")
        print(info["book_name"])

        chapter = await client.get_chapter("1", book_id="12345")
        print(chapter["content"][:200])

        await client.download_book("12345")
        client.export_book("12345", formats=["txt"])

asyncio.run(main())
```

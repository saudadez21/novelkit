import logging
from typing import Any

from novelkit.plugins.base.fetcher import BaseFetcher
from novelkit.plugins.registry import hub

logger = logging.getLogger(__name__)


@hub.register_fetcher()
class BilibiliFetcher(BaseFetcher):
    site_key = "bilibili"
    site_name = "哔哩哔哩 (专栏)"
    BASE_URL = "https://www.bilibili.com"

    REQUIRE_BOOK_ID = False

    BOOK_INFO_URL = "https://api.bilibili.com/x/article/list/web/articles"
    CHAPTER_URL = "https://www.bilibili.com/opus/{chapter_id}/"

    async def fetch_book_info(
        self,
        book_id: str,
        **kwargs: Any,
    ) -> list[str]:
        if book_id.startswith("rl"):
            book_id = book_id[2:]
        headers = {
            **self.session.headers,
            "Origin": "https://www.bilibili.com",
        }
        params = {"id": book_id}
        return [
            await self.fetch_text(
                self.BOOK_INFO_URL, headers=headers, params=params, **kwargs
            )
        ]

    async def fetch_chapter_content(
        self,
        chapter_id: str,
        book_id: str | None = None,
        **kwargs: Any,
    ) -> list[str]:
        headers = {
            **self.session.headers,
            "Origin": "https://www.bilibili.com",
        }
        url = self.CHAPTER_URL.format(chapter_id=chapter_id)
        return [await self.fetch_text(url, headers=headers, **kwargs)]

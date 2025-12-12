import logging
from typing import Any

from novelkit.plugins.base.fetcher import BaseFetcher
from novelkit.plugins.registry import hub

logger = logging.getLogger(__name__)


@hub.register_fetcher()
class B520Fetcher(BaseFetcher):
    site_key = "b520"
    site_name = "笔趣阁 (b520)"
    BASE_URL = "http://www.b520.cc"

    BOOK_INFO_URL = "http://www.b520.cc/{book_id}/"
    CHAPTER_URL = "http://www.b520.cc/{book_id}/{chapter_id}.html"

    SEARCH_URL = "http://www.b520.cc/modules/article/search.php"

    async def fetch_book_info(
        self,
        book_id: str,
        **kwargs: Any,
    ) -> list[str]:
        book_id = self._add_prefix(book_id, sep="_")
        headers = {
            **self.session.headers,
            "Referer": "http://www.b520.cc/",
        }
        url = self.BOOK_INFO_URL.format(book_id=book_id)
        return [await self.fetch_text(url, headers=headers, **kwargs)]

    async def fetch_chapter_content(
        self,
        chapter_id: str,
        book_id: str | None = None,
        **kwargs: Any,
    ) -> list[str]:
        if not book_id:
            raise ValueError(
                f"{self.site_name}: book_id is required for chapter fetch, "
                f"but got book_id={book_id!r}."
            )

        book_id = self._add_prefix(book_id, sep="_")
        headers = {
            **self.session.headers,
            "Referer": "http://www.b520.cc/",
        }
        url = self.CHAPTER_URL.format(book_id=book_id, chapter_id=chapter_id)
        return [await self.fetch_text(url, headers=headers, encoding="gbk", **kwargs)]

    async def fetch_search_result(
        self,
        keyword: str,
        **kwargs: Any,
    ) -> list[str]:
        params = {"searchkey": keyword}
        headers = {
            **self.session.headers,
            "Referer": "http://www.b520.cc/",
        }
        resp = await self.session.get(
            self.SEARCH_URL, params=params, headers=headers, **kwargs
        )
        if not resp.ok:
            logger.info(
                "Failed to fetch HTML for keyword '%s' from '%s'",
                keyword,
                self.SEARCH_URL,
            )
            return []
        return [resp.text]

import logging
from typing import Any

from novelkit.plugins.base.fetcher import GenericFetcher
from novelkit.plugins.registry import hub

logger = logging.getLogger(__name__)


@hub.register_fetcher()
class AliceswFetcher(GenericFetcher):
    site_key = "alicesw"
    site_name = "爱丽丝书屋"
    BASE_URL = "https://www.alicesw.com"

    BASE_URL_MAP = {
        "simplified": "https://www.alicesw.com",
        "traditional": "https://www.alicesw.tw",
    }

    BOOK_ID_REPLACEMENTS = [("-", "/")]
    CHAP_ID_REPLACEMENTS = [("-", "/")]

    HAS_SEPARATE_CATALOG = True
    REQUIRE_BOOK_ID = False

    BOOK_INFO_PATH = "/novel/{book_id}.html"
    BOOK_CATALOG_PATH = "/other/chapters/id/{book_id}.html"
    CHAPTER_PATH = "/book/{chapter_id}.html"

    SEARCH_URL = "https://www.alicesw.com/search.html"

    async def fetch_search_result(
        self,
        keyword: str,
        **kwargs: Any,
    ) -> list[str]:
        params = {"q": keyword, "f": "_all"}
        resp = await self.session.get(self.SEARCH_URL, params=params)
        if not resp.ok:
            logger.info(
                "Failed to fetch HTML for keyword '%s' from '%s'",
                keyword,
                self.SEARCH_URL,
            )
            return []
        return [resp.text]

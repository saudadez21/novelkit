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
    CHAPTER_PATH = "/yuedu/{book_id}_{chapter_id}.html"

    SEARCH_URL = "http://www.aaatxt.com/search.php"

    async def fetch_search_result(
        self,
        keyword: str,
        **kwargs: Any,
    ) -> list[str]:
        # gbk / gb2312
        params = {
            "keyword": self._quote(keyword, encoding="gb2312", errors="replace"),
            "submit": self._quote("搜 索", encoding="gb2312", errors="replace"),
        }
        full_url = self._build_url(self.SEARCH_URL, params)  # need build manually
        headers = {
            **self.session.headers,
            "Host": "www.aaatxt.com",
            "Referer": "http://www.aaatxt.com/",
        }
        resp = await self.session.get(full_url, headers=headers, **kwargs)
        if not resp.ok:
            logger.info(
                "Failed to fetch HTML for keyword '%s' from '%s'",
                keyword,
                self.SEARCH_URL,
            )
            return []
        return [resp.text]

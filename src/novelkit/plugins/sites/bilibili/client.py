from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from novelkit.infra.http_defaults import DEFAULT_HEADERS
from novelkit.plugins.base.client import BaseClient
from novelkit.plugins.base.errors import EmptyContent, RestrictedContent
from novelkit.plugins.registry import hub
from novelkit.schemas import ChapterDict

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from novelkit.plugins.protocols import _ClientContext


@hub.register_client()
class BilibiliClient(BaseClient):
    site_key = "bilibili"
    r18 = False
    support_search = False

    MEDIA_BASE_HEADERS = {
        **DEFAULT_HEADERS,
        "Origin": "https://www.bilibili.com",
    }

    async def get_chapter(
        self: _ClientContext,
        chapter_id: str,
        book_id: str | None = None,
        **kwargs: Any,
    ) -> ChapterDict | None:
        for attempt in range(self._retry_times + 1):
            try:
                raw_pages = await self.fetcher.fetch_chapter_content(
                    book_id=book_id, chapter_id=chapter_id
                )
                self._save_raw_pages(chapter_id, raw_pages, book_id=book_id)

                chap = await asyncio.to_thread(
                    self.parser.parse_chapter_content,
                    raw_pages,
                    book_id=book_id,
                    chapter_id=chapter_id,
                )

                return chap

            except EmptyContent as exc:
                logger.warning(
                    "Empty content (site=%s, book=%s, chapter=%s): %s",
                    self.site_key,
                    book_id,
                    chapter_id,
                    exc,
                )
                return None

            except RestrictedContent as exc:
                logger.warning(
                    "Restricted chapter (site=%s, book=%s, chapter=%s): %s",
                    self.site_key,
                    book_id,
                    chapter_id,
                    exc,
                )
                if attempt < self._retry_times:
                    await self._sleep(interval=60)  # wait 1 minite
                else:
                    return None

            except Exception as e:
                if attempt < self._retry_times:
                    logger.info(
                        "Retrying (site=%s, book=%s, chapter=%s, attempt=%d): %s",
                        self.site_key,
                        book_id,
                        chapter_id,
                        attempt + 1,
                        e,
                    )
                    await self._sleep(interval=self._backoff_factor * (2**attempt))
                else:
                    logger.warning(
                        "Failed chapter (site=%s, book=%s, chapter=%s): %s",
                        self.site_key,
                        book_id,
                        chapter_id,
                        e,
                    )
        return None

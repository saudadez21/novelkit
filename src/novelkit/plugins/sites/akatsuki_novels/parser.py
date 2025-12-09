from typing import Any

from lxml import html

from novelkit.plugins.base.errors import EmptyContent
from novelkit.plugins.base.parser import BaseParser
from novelkit.plugins.registry import hub
from novelkit.schemas import (
    BookInfoDict,
    ChapterDict,
    ChapterInfoDict,
    VolumeInfoDict,
)


@hub.register_parser()
class AkatsukiNovelsParser(BaseParser):
    site_key = "akatsuki_novels"
    site_name = "暁"
    BASE_URL = "https://www.akatsuki-novels.com"

    def parse_book_info(
        self,
        raw_pages: list[str],
        book_id: str,
        **kwargs: Any,
    ) -> BookInfoDict:
        if not raw_pages:
            raise EmptyContent(
                f"{self.site_key}: empty book-info page (book_id={book_id})"
            )

        tree = html.fromstring(raw_pages[0])

        book_name = self._first_str(tree.xpath('//h3[@class="font-bb"]/a/text()'))
        author = self._first_str(
            tree.xpath('//h3[@class="font-bb"][contains(., "作者")]/a/text()')
        )
        summary = self._join_strs(
            tree.xpath(
                '//div[contains(normalize-space(@class), "body-x1 body-normal body-w640")]/div/div[1]//text()'  # noqa: E501
            )
        )

        # --- Volumes & Chapters ---
        volumes: list[VolumeInfoDict] = []
        vol_idx: int = 1
        vol_name: str | None = None
        vol_chaps: list[ChapterInfoDict] = []

        def flush_volume() -> None:
            nonlocal vol_idx, vol_name, vol_chaps
            if not vol_chaps:
                return

            volumes.append(
                {
                    "volume_name": vol_name or f"未命名卷 {vol_idx}",
                    "chapters": vol_chaps,
                }
            )

            vol_name = None
            vol_chaps = []
            vol_idx += 1

        for page_html in raw_pages:
            tree = html.fromstring(page_html)
            for tr in tree.xpath('//table[@class="list"]//tbody//tr'):
                # detect volume title
                a = tr.find(".//a")
                if a is None:
                    text = tr.text_content().strip()
                    if text == vol_name:  # happend at multi page first line
                        continue
                    if text:
                        flush_volume()
                        vol_name = text
                    continue

                url = a.get("href", "").strip()
                if not url:
                    continue

                # /stories/view/1471/novel_id~103 -> "1471"
                parts = url.split("/")
                chapter_id = parts[3] if len(parts) > 3 else ""
                title = a.text_content().strip()

                vol_chaps.append(
                    {
                        "title": title,
                        "url": self._abs_url(url),
                        "chapterId": chapter_id,
                        "accessible": True,
                    }
                )

        flush_volume()
        if not volumes:
            raise EmptyContent(f"{self.site_key}: empty volumes (book_id={book_id})")

        return {
            "book_id": book_id,
            "book_name": book_name,
            "author": author,
            "cover_url": "",
            "update_time": "",
            "serial_status": "",
            "word_count": "",
            "summary": summary,
            "tags": [],
            "volumes": volumes,
            "extra": {},
        }

    def parse_chapter_content(
        self,
        raw_pages: list[str],
        chapter_id: str,
        book_id: str | None = None,
        **kwargs: Any,
    ) -> ChapterDict:
        if not raw_pages:
            raise EmptyContent(
                f"{self.site_key}: empty chapter page "
                f"(book_id={book_id}, chapter_id={chapter_id})"
            )

        tree = html.fromstring(raw_pages[0])

        title = self._first_str(tree.xpath("//h2/text()"))

        paragraphs = [
            s
            for p in tree.xpath('//div[@class="body-novel"]//text()')
            if (s := p.strip())
        ]

        if not paragraphs:
            raise EmptyContent(
                f"{self.site_key}: empty chapter content "
                f"(book_id={book_id}, chapter_id={chapter_id})"
            )

        content = "\n".join(paragraphs)

        return {
            "id": chapter_id,
            "title": title,
            "content": content,
            "extra": {"site": self.site_key},
        }

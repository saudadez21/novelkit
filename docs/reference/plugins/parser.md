# Parser

A **Parser** transforms raw HTML or JSON returned by a fetcher into
structured Python dictionaries used by downstream components such as the
processor and export.

Most site-specific implementations inherit from `BaseParser`, while
the exact interface is defined by the parser protocol.

---

::: novelkit.plugins.protocols.parser.ParserProtocol

---

## Example: Implementing a Simple Parser

Below is a real-world example using **lxml + XPath** together with helper
methods from `BaseParser`.

This parser extracts:

- book title / author / cover / summary
- a single-volume catalog
- chapter title + cleaned text
- search results

```py
from __future__ import annotations
from typing import Any

from lxml import html
from novelkit.plugins.base.parser import BaseParser
from novelkit.plugins.registry import hub
from novelkit.schemas import BookInfoDict, ChapterDict, SearchResult

@hub.register_parser()
class AaatxtParser(BaseParser):
    priority = 500

    site_key = "aaatxt"
    site_name = "3A电子书"
    BASE_URL = "http://www.aaatxt.com"

    ADS = {
        "按键盘上方向键",
        "未阅读完",
        "加入书签",
        "已便下次继续阅读",
        "更多原创手机电子书",
        "免费TXT小说下载",
    }

    # ---------------------------------------------------------
    # Book Info
    # ---------------------------------------------------------
    def parse_book_info(
        self,
        raw_pages: list[str],
        book_id: str,
        **kwargs: Any,
    ) -> BookInfoDict | None:
        if not raw_pages:
            return None

        tree = html.fromstring(raw_pages[0])

        book_name = self._first_str(tree.xpath("//div[@class='xiazai']/h1/text()"))
        author = self._first_str(tree.xpath("//span[@id='author']/a/text()"))
        cover_url = self._first_str(
            tree.xpath("//div[@id='txtbook']//div[@class='fm']//img/@src")
        )

        update_time = self._first_str(
            tree.xpath("//div[@id='txtbook']//li[contains(text(), '上传日期')]/text()"),
            replaces=[("上传日期:", "")],
        )

        genre = self._first_str(
            tree.xpath("//div[@id='submenu']/h2/a[@class='lan']/text()")
        )
        tags = [genre] if genre else []

        summary = self._first_str(tree.xpath("//div[@id='jj']//p/text()"))

        # Extract catalog as a single volume
        chapters = []
        for a in tree.xpath("//div[@id='ml']//ol/li/a"):
            url = a.get("href", "").strip()
            chapter_id = url.split("_")[-1].replace(".html", "")
            title = a.text_content().strip()
            chapters.append(
                {
                    "title": title,
                    "url": url,
                    "chapterId": chapter_id,
                    "accessible": True,
                }
            )

        volumes = [{"volume_name": "正文", "chapters": chapters}]

        return {
            "book_id": book_id,
            "book_name": book_name,
            "author": author,
            "cover_url": cover_url,
            "update_time": update_time,
            "serial_status": "",
            "word_count": "",
            "tags": tags,
            "summary": summary,
            "volumes": volumes,
            "extra": {},
        }

    # ---------------------------------------------------------
    # Chapter Content
    # ---------------------------------------------------------
    def parse_chapter_content(
        self,
        raw_pages: list[str],
        chapter_id: str,
        book_id: str | None = None,
        **kwargs: Any,
    ) -> ChapterDict | None:
        if not raw_pages:
            return None

        tree = html.fromstring(raw_pages[0])

        raw_title = self._first_str(tree.xpath("//div[@id='content']//h1/text()"))
        title = raw_title.split("-", 1)[-1].strip()

        paragraphs = []
        for txt in tree.xpath("//div[@class='chapter']//text()"):
            line = txt.strip()
            if not line or self._is_ad_line(txt):
                continue
            paragraphs.append(line)

        if not paragraphs:
            return None

        content = "\n".join(paragraphs)

        return {
            "id": chapter_id,
            "title": title,
            "content": content,
            "extra": {"site": self.site_key},
        }

    # ---------------------------------------------------------
    # Search Results
    # ---------------------------------------------------------
    def parse_search_result(
        self,
        raw_pages: list[str],
        limit: int | None = None,
        **kwargs: Any,
    ) -> list[SearchResult]:
        if not raw_pages:
            return []

        doc = html.fromstring(raw_pages[0])
        rows = doc.xpath("//div[@class='sort']//div[@class='list']/table")
        results: list[SearchResult] = []

        for idx, row in enumerate(rows):
            if limit is not None and idx >= limit:
                break

            href = self._first_str(row.xpath(".//td[@class='name']/h3/a/@href"))
            if not href:
                continue

            book_id = href.split("/")[-1].split(".")[0]
            book_url = self._abs_url(href)

            cover_rel = self._first_str(row.xpath(".//td[@class='cover']/a/img/@src"))
            cover_url = self._abs_url(cover_rel) if cover_rel else ""

            title = self._first_str(row.xpath(".//td[@class='name']/h3/a//text()"))

            results.append(
                SearchResult(
                    site=self.site_key,
                    book_id=book_id,
                    book_url=book_url,
                    cover_url=cover_url,
                    title=title,
                    author="-",
                    latest_chapter="-",
                    update_date="-",
                    word_count="-",
                    priority=self.priority + idx,
                )
            )

        return results
```

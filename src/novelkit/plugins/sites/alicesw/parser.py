from typing import Any

from lxml import html

from novelkit.plugins.base.errors import EmptyContent
from novelkit.plugins.base.parser import BaseParser
from novelkit.plugins.registry import hub
from novelkit.schemas import (
    BookInfoDict,
    ChapterDict,
    ChapterInfoDict,
    SearchResult,
    VolumeInfoDict,
)


@hub.register_parser()
class AliceswParser(BaseParser):
    priority = 500

    site_name = "爱丽丝书屋"
    site_key = "alicesw"
    BASE_URL = "https://www.alicesw.com"

    def parse_book_info(
        self,
        raw_pages: list[str],
        book_id: str,
        **kwargs: Any,
    ) -> BookInfoDict:
        if len(raw_pages) < 2:
            raise EmptyContent(
                f"{self.site_key}: empty book-info page (book_id={book_id})"
            )

        info_tree = html.fromstring(raw_pages[0])
        catalog_tree = html.fromstring(raw_pages[1])

        # Metadata extraction
        book_name = self._first_str(
            info_tree.xpath("//div[@id='detail-box']//h1/text()")
        )
        author = self._first_str(
            info_tree.xpath(
                "//div[@id='detail-box']//p/a[contains(@href,'author')]/text()"
            )
        )
        cover_url = self._first_str(
            info_tree.xpath(
                "//div[@class='pic']//img[contains(@class,'fengmian2')]/@src"
            )
        )

        tags = info_tree.xpath("//p[contains(text(),'标签')]/a/text()")
        tags = [s for t in tags if (s := t.strip())]

        serial_status = self._first_str(
            info_tree.xpath("//div[@class='pic']/div[contains(text(),'状态')]/text()"),
            replaces=[("小说状态：", "")],
        )
        word_count = self._first_str(
            info_tree.xpath("//div[@class='pic']/div[contains(text(),'字数')]/text()"),
            replaces=[("小说字数：", "")],
        )
        update_time = self._first_str(
            info_tree.xpath(
                "//div[@id='detail-box']//div[contains(text(),'更新时间')]/text()"
            ),
            replaces=[("更新时间：", "")],
        )

        summary = self._join_strs(info_tree.xpath("//div[@class='intro']//text()"))

        chapters: list[ChapterInfoDict] = []
        for a in catalog_tree.xpath("//ul[@class='mulu_list']/li/a"):
            href = a.get("href", "").strip()
            if not href:
                continue

            title = a.text_content().strip()
            chapter_id = href.split(".")[0].split("book/")[-1].replace("/", "-")
            abs_url = self._abs_url(href)

            chapters.append(
                {
                    "title": title,
                    "url": abs_url,
                    "chapterId": chapter_id,
                    "accessible": True,
                }
            )

        if not chapters:
            raise EmptyContent(f"{self.site_key}: empty volumes (book_id={book_id})")

        volumes: list[VolumeInfoDict] = [{"volume_name": "正文", "chapters": chapters}]

        return {
            "book_id": book_id,
            "book_name": book_name,
            "author": author,
            "cover_url": cover_url,
            "update_time": update_time,
            "word_count": word_count,
            "serial_status": serial_status,
            "tags": tags,
            "summary": summary,
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

        title = self._first_str(tree.xpath("//h3[@class='j_chapterName']/text()"))
        paragraphs = [
            text
            for p in tree.xpath("//div[contains(@class,'read-content')]//p")
            if (text := self._norm_space(p.text_content()))
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

    def parse_search_result(
        self,
        raw_pages: list[str],
        limit: int | None = None,
        **kwargs: Any,
    ) -> list[SearchResult]:
        if not raw_pages:
            return []
        doc = html.fromstring(raw_pages[0])
        rows = doc.xpath("//div[contains(@class, 'list-group-item')]")
        results: list[SearchResult] = []

        for idx, row in enumerate(rows):
            if limit is not None and idx >= limit:
                break
            href = self._first_str(row.xpath(".//h5/a/@href"))
            if not href:
                continue

            book_id = href.rsplit("/", 1)[-1].split(".", 1)[0]
            book_url = self._abs_url(href)
            title = self._join_strs(row.xpath(".//h5/a//text()"))
            author = self._first_str(
                row.xpath(".//p[contains(@class,'text-muted')]/a/text()")
            )
            update_date = self._first_str(
                row.xpath(
                    ".//p[contains(@class,'timedesc')]/text()[contains(., '更新时间')]"
                )
            )
            update_date = update_date.split("更新时间：", 1)[-1]

            results.append(
                SearchResult(
                    site_key=self.site_key,
                    site_name=self.site_name,
                    book_id=book_id,
                    book_url=book_url,
                    cover_url="",
                    title=title,
                    author=author,
                    update_date=update_date,
                    priority=self.priority + idx,
                )
            )
        return results

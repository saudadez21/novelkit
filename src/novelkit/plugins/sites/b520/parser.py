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
class B520Parser(BaseParser):
    priority = 30

    site_key = "b520"
    site_name = "笔趣阁 (b520)"
    BASE_URL = "http://www.b520.cc"

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

        book_name = self._first_str(tree.xpath('//div[@id="info"]/h1/text()'))

        author = self._first_str(
            tree.xpath('//div[@id="info"]/p[1]/text()'),
            replaces=[("\xa0", ""), ("作者：", "")],
        )

        cover_url = self._first_str(tree.xpath('//div[@id="fmimg"]/img/@src'))

        update_time = self._first_str(
            tree.xpath('//div[@id="info"]/p[3]/text()'),
            replaces=[("最后更新：", "")],
        )

        summary = self._join_strs(tree.xpath("//div[@id='intro']//p/text()"))

        book_type = self._first_str(tree.xpath('//div[@class="con_top"]/a[2]/text()'))
        tags = [book_type] if book_type else []

        chapters: list[ChapterInfoDict] = [
            {
                "title": (a.text or "").strip(),
                "url": (a.get("href") or "").strip(),
                "chapterId": (a.get("href") or "").rsplit("/", 1)[-1].split(".", 1)[0],
                "accessible": True,
            }
            for a in tree.xpath(
                '//div[@id="list"]/dl/dt[contains(., "正文")]/following-sibling::dd/a'
            )
        ]

        if not chapters:
            raise EmptyContent(f"{self.site_key}: empty volumes (book_id={book_id})")

        volumes: list[VolumeInfoDict] = [{"volume_name": "正文", "chapters": chapters}]

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

        title = self._first_str(tree.xpath('//div[@class="bookname"]/h1/text()'))

        paragraphs = [
            text
            for p in tree.xpath('//div[@id="content"]//p')
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
        rows = doc.xpath('//table[@class="grid"]//tr[position()>1]')
        results: list[SearchResult] = []

        for idx, row in enumerate(rows):
            if limit is not None and idx >= limit:
                break

            href = self._first_str(row.xpath(".//td[1]/a[1]/@href"))
            if not href:
                continue

            book_id = href.strip("/").split("/")[-1]
            book_url = self._abs_url(href)
            title = self._first_str(row.xpath(".//td[1]/a[1]/text()"))
            author = self._first_str(row.xpath(".//td[3]//text()"))
            update_date = self._first_str(row.xpath(".//td[5]//text()"))

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

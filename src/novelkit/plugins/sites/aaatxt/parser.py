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

        # Chapters from the book_list
        chapters: list[ChapterInfoDict] = []
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

        raw_title = self._first_str(tree.xpath("//div[@id='content']//h1/text()"))
        title = raw_title.split("-", 1)[-1].strip()

        paragraphs = []
        for txt in tree.xpath("//div[@class='chapter']//text()"):
            line = txt.strip()
            # Skip empty/instruction/ad lines
            if not line or self._is_ad_line(txt):
                continue
            paragraphs.append(line)

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

            size_text = row.xpath("string(.//td[@class='size'])")
            size_norm = size_text.replace("\u00a0", " ").replace("&nbsp;", " ").strip()
            tokens = [t for t in size_norm.split() if t]

            author = "-"
            for tok in tokens:
                if tok.startswith("上传:"):
                    author = tok.split(":", 1)[1].strip()

            intro_text = row.xpath("string(.//td[@class='intro'])")
            intro_norm = intro_text.replace("\u00a0", " ").replace("&nbsp;", " ")
            update_date = "-"
            for marker in ("更新:", "更新："):
                if marker in intro_norm:
                    tail = intro_norm.split(marker, 1)[1].strip()
                    update_date = tail.split()[0] if tail else "-"
                    break

            results.append(
                SearchResult(
                    site_key=self.site_key,
                    site_name=self.site_name,
                    book_id=book_id,
                    book_url=book_url,
                    cover_url=cover_url,
                    title=title,
                    author=author,
                    update_date=update_date,
                    priority=self.priority + idx,
                )
            )
        return results

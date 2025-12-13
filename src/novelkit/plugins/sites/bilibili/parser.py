import json
from datetime import datetime
from typing import Any

from lxml import html

from novelkit.plugins.base.errors import EmptyContent, RestrictedContent
from novelkit.plugins.base.parser import BaseParser
from novelkit.plugins.registry import hub
from novelkit.schemas import (
    BookInfoDict,
    ChapterDict,
    ChapterInfoDict,
    MediaResource,
    VolumeInfoDict,
)


@hub.register_parser()
class BilibiliParser(BaseParser):
    site_key = "bilibili"
    site_name = "哔哩哔哩 (专栏)"
    BASE_URL = "https://www.bilibili.com"

    CONTENT_ROOT_XPATHS = [
        # https://www.bilibili.com/opus/{chapter_id}/
        # e.x. https://www.bilibili.com/opus/784249621048197123/
        "//div[contains(@class,'opus-module-content') and contains(@class,'opus-paragraph-children')]",  # noqa: E501
        # https://www.bilibili.com/read/{chapter_id}/
        # e.x. https://www.bilibili.com/read/cv21590989/
        "//div[@id='read-article-holder']",
        "//div[@id='article-content']",
    ]

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

        resp = json.loads(raw_pages[0])
        code = resp.get("code")
        if code != 0:
            raise RestrictedContent(
                f"{self.site_key}: api error (book_id={book_id}, code={code})"
            )

        data: dict[str, Any] = resp.get("data", {})
        if not data:
            raise EmptyContent(f"{self.site_key}: empty data field (book_id={book_id})")

        book = data.get("list")
        author_info = data.get("author")
        articles = data.get("articles", [])

        if not book or not articles:
            raise EmptyContent(
                f"{self.site_key}: empty book or chapters (book_id={book_id})"
            )

        book_name: str = book.get("name", "")
        summary: str = book.get("summary", "")
        cover_url: str = book.get("image_url", "")

        word_count: str = str(book.get("words", 0))
        author: str = author_info.get("name", "") if author_info else ""

        update_ts = book.get("update_time")
        update_time: str = ""
        if isinstance(update_ts, (int, float)) and update_ts > 0:
            update_time = datetime.fromtimestamp(update_ts).strftime("%Y-%m-%d")

        # Chapters from the book_list
        tags_set: set[str] = set()
        chapters: list[ChapterInfoDict] = []
        for a in articles:
            dyn_id = a.get("dyn_id_str")
            if not dyn_id:
                continue

            title = a.get("title", "")
            url = f"{self.BASE_URL}/opus/{dyn_id}/"

            for c in a.get("categories", []):
                name = c.get("name")
                if name:
                    tags_set.add(name)

            chapters.append(
                {
                    "title": title,
                    "url": url,
                    "chapterId": dyn_id,
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
            "word_count": word_count,
            "tags": sorted(tags_set),
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
                f"{self.site_key}: empty chapter page (chapter_id={chapter_id})"
            )

        html_text = raw_pages[0]
        if "验证码_哔哩哔哩" in html_text:
            raise RestrictedContent(
                f"{self.site_key}: captcha required (chapter_id={chapter_id})"
            )

        tree = html.fromstring(html_text)

        title = self._first_str(
            tree.xpath(
                "//div[contains(@class,'opus-module-title__inner')]//span/text()"
                " | //h1[@class='title']/text()"
            )
        )

        paragraphs: list[str] = []
        current_idx: int = 0
        resources: list[MediaResource] = []

        content_roots = []
        for xp in self.CONTENT_ROOT_XPATHS:
            content_roots = tree.xpath(xp)
            if content_roots:
                break

        for root in content_roots:
            current_idx = self._extract_chapter_blocks(
                root, paragraphs, resources, current_idx
            )

        if not (paragraphs or resources):
            raise EmptyContent(
                f"{self.site_key}: empty chapter content (chapter_id={chapter_id})"
            )

        content = "\n".join(paragraphs)

        return {
            "id": chapter_id,
            "title": title,
            "content": content,
            "extra": {
                "site": self.site_key,
                "resources": resources,
            },
        }

    def _extract_chapter_blocks(
        self,
        root: html.HtmlElement,
        paragraphs: list[str],
        resources: list[MediaResource],
        start_idx: int,
    ) -> int:
        current_idx = start_idx
        for el in root.iterchildren():
            tag = str(el.tag).lower()
            cls = el.get("class", "")

            # ---- paragraph ----
            if tag in ("p", "h1", "h2", "h3", "h4", "h5", "h6"):
                text = el.text_content().strip()
                if text:
                    paragraphs.append(text)
                    current_idx += 1
                continue

            # ---- image block ----
            if tag == "div" and "pic" in cls:
                for src in el.xpath(".//img/@src"):
                    resources.append(
                        {
                            "type": "image",
                            "url": self._abs_url(src),
                            "paragraph_index": current_idx,
                        }
                    )
                continue

            # ---- fallback ----
            text = el.text_content().strip()
            if text:
                paragraphs.append(text)
                current_idx += 1

        return current_idx

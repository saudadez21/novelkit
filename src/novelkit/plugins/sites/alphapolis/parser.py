from typing import Any

from lxml import html

from novelkit.plugins.base.errors import EmptyContent
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
class AlphapolisParser(BaseParser):
    site_key = "alphapolis"
    site_name = "アルファポリス"
    BASE_URL = "https://www.alphapolis.co.jp"

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

        book_name = self._first_str(tree.xpath("//h1[contains(@class,'title')]/text()"))
        author = self._first_str(
            tree.xpath("//div[contains(@class,'author')]//a[1]/text()")
        )
        cover_url = self._first_str(tree.xpath('//meta[@property="og:image"]/@content'))

        update_time = self._first_str(
            tree.xpath(
                './/table[contains(@class,"detail")]'
                '//tr[th[text()="更新日時"]]/td/text()'
            )
        )
        summary = self._first_str(tree.xpath('//meta[@name="description"]/@content'))
        summary = self._clean_invisible(summary)
        tag_nodes = tree.xpath(
            '//div[contains(@class,"content-tags")]//span[contains(@class,"tag")]/a/text()'
        )
        tags = [s for t in tag_nodes if (s := t.strip())]

        # --- Volumes & Chapters ---
        volumes: list[VolumeInfoDict] = []
        vol_idx: int = 1
        vol_name: str | None = None
        vol_intro: str | None = None
        vol_chaps: list[ChapterInfoDict] = []

        def flush_volume() -> None:
            nonlocal vol_idx, vol_name, vol_intro, vol_chaps
            if not vol_chaps:
                return

            vol: VolumeInfoDict = {
                "volume_name": vol_name or f"未命名卷 {vol_idx}",
                "chapters": vol_chaps,
            }
            if vol_intro:
                vol["volume_intro"] = vol_intro
            volumes.append(vol)

            vol_name = None
            vol_intro = None
            vol_chaps = []
            vol_idx += 1

        for elem in tree.xpath('//div[@class="episodes"]/*'):
            elem_cls = elem.get("class") or ""
            tag = (elem.tag or "").lower()

            if tag == "div" and "chapter-rental" in elem_cls:
                flush_volume()
                h3 = elem.find("h3")
                vol_name = h3.text_content().strip() if h3 is not None else None
                continue

            if tag == "div" and "rental" in elem_cls:
                intro = elem.xpath('.//div[@class="rental-book"]//p/text()')
                vol_intro = "\n".join(s.strip() for s in intro if s.strip()) or None

                for ep in elem.xpath('.//div[contains(@class,"rental-episode")]'):
                    a = next(ep.iter("a"), None)
                    if a is None:
                        continue

                    href = a.get("data-href") or a.get("href")
                    if "extra_episode" in href:  # TODO: support extra
                        continue

                    title = a.xpath("string(.//h3)").strip()
                    chapter_id = href.rsplit("/", 1)[-1]
                    abs_url = self._abs_url(href)

                    has_paywall = bool(ep.xpath('.//div[contains(@class, "use-ac")]'))

                    vol_chaps.append(
                        {
                            "title": title,
                            "url": abs_url,
                            "chapterId": chapter_id,
                            "accessible": not has_paywall,
                        }
                    )
                continue

            if tag == "h3":
                flush_volume()
                vol_name = elem.text_content().strip()
                continue

            if tag == "div" and "episode" in elem_cls:
                a = elem.xpath(".//a")[0]
                href = a.get("href", "").strip()
                if "extra_episode" in href:  # TODO: support extra
                    continue

                chapter_id = href.rsplit("/", 1)[-1]
                title = a.xpath('string(.//span[@class="title"])').strip()
                abs_url = self._abs_url(href)
                has_paywall = bool(elem.xpath('.//div[contains(@class, "use-ac")]'))
                vol_chaps.append(
                    {
                        "title": title,
                        "url": abs_url,
                        "chapterId": chapter_id,
                        "accessible": not has_paywall,
                    }
                )
                continue

        flush_volume()

        if not volumes:
            raise EmptyContent(f"{self.site_key}: empty volumes (book_id={book_id})")

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

        title = self._first_str(
            tree.xpath("//h2[contains(@class,'episode-title')]/text()")
        )

        paragraphs: list[str] = []
        curr_para: list[str] = []
        resources: list[MediaResource] = []
        curr_idx = 0

        def flush() -> None:
            nonlocal curr_para, curr_idx
            text = self._clean_invisible("".join(curr_para)).strip()

            if text:
                paragraphs.append(text)
                curr_idx += 1
            curr_para = []

        def extract_ruby(node: html.HtmlElement) -> str:
            base = (node.text or "").strip()
            rt = "".join(node.xpath("./rt/text()")).strip()
            if rt:
                return f"{base} ({rt})"
            return base

        def walk(node: html.HtmlElement) -> None:
            tag = node.tag

            # ---------- Case 1: <img> ----------
            if tag == "img":
                flush()
                src = node.get("src") or node.get("data-src")
                if src:
                    resources.append(
                        {
                            "type": "image",
                            "url": self._abs_url(src),
                            "paragraph_index": curr_idx,
                        }
                    )
                return

            # ---------- Case 2: <ruby> ----------
            if tag == "ruby":
                curr_para.append(extract_ruby(node))

                # process tail
                if node.tail and node.tail.strip():
                    curr_para.append(node.tail)
                return

            # ---------- Case 3: <br> ----------
            if tag == "br":
                flush()
                return

            # ---------- Case 4: text before children ----------
            if node.text and node.text.strip():
                curr_para.append(node.text)

            # ---------- Case 5: walk children ----------
            for child in node:
                walk(child)
                if child.tag != "ruby" and child.tail and child.tail.strip():
                    curr_para.append(child.tail)

        for body in tree.xpath('//div[@id="novelBody"]'):
            walk(body)
            flush()

        if not (paragraphs or resources):
            raise EmptyContent(
                f"{self.site_key}: empty chapter content "
                f"(book_id={book_id}, chapter_id={chapter_id})"
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

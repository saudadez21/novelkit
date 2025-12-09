from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from novelkit.infra.persistence.chapter_storage import ChapterStorage
from novelkit.libs.filesystem import format_filename, sanitize_filename
from novelkit.schemas import (
    BookConfig,
    BookInfoDict,
    ChapterDict,
    ExporterConfig,
    VolumeInfoDict,
)

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from novelkit.plugins.protocols import _ClientContext

    class ExportTxtClientContext(_ClientContext, Protocol):
        """"""

        def _xp_txt_header(self, book_info: BookInfoDict) -> str: ...

        def _xp_txt_volume_header(
            self, vol_title: str, volume: VolumeInfoDict
        ) -> str: ...

        def _xp_txt_chapter_header(self, chap: ChapterDict) -> str: ...

        def _xp_txt_chapter(self, chap: ChapterDict, title_fallback: str) -> str: ...

        def _xp_txt_missing_chapter(self, title: str) -> str: ...

        def _xp_txt_chapter_footer(self, chap: ChapterDict) -> str: ...


class ExportTxtMixin:
    """Mixin providing TXT export utilities."""

    def _export_book_txt(
        self: ExportTxtClientContext,
        book: BookConfig,
        cfg: ExporterConfig,
        *,
        stage: str | None = None,
        **kwargs: Any,
    ) -> list[Path]:
        """
        Export a novel as a single text file by merging all chapter data.
        """
        book_id = book.book_id

        # --- Load book data ---
        raw_base = self._raw_data_dir / book_id
        if not raw_base.is_dir():
            return []

        stage = stage or self._detect_latest_stage(book_id)
        book_info = self._load_book_info(book_id, stage=stage)

        # --- Filter volumes ---
        orig_vols = book_info.get("volumes", [])
        vols = self._filter_volumes(
            orig_vols, book.start_id, book.end_id, book.ignore_ids
        )
        if not vols:
            logger.info(
                "Nothing to do after filtering (site=%s, book=%s)",
                self.site_key,
                book_id,
            )
            return []

        parts: list[str] = [self._xp_txt_header(book_info)]

        # --- Build body by volumes & chapters ---
        for v_idx, vol, chap_map in self._iter_volume_chapters(raw_base, stage, vols):
            # Volume heading
            vol_title = vol.get("volume_name") or f"卷 {v_idx}"
            parts.append(self._xp_txt_volume_header(vol_title, vol))

            # Iterate chapters inside this volume
            for ch_info in vol.get("chapters", []):
                cid = ch_info.get("chapterId")
                if not cid:
                    continue

                ch = chap_map.get(cid)
                ch_title = ch_info.get("title") or f"Chapter {cid}"
                if not ch:
                    # Render placeholder for missing chapters
                    if cfg.render_missing_chapter:
                        parts.append(self._xp_txt_missing_chapter(ch_title))
                    continue

                # Normal chapter
                parts.append(self._xp_txt_chapter(ch, ch_title))

        final_text = "\n\n".join(parts) + "\n"

        # --- Save final text ---
        out_name = format_filename(
            cfg.filename_template,
            title=book_info["book_name"],
            author=book_info.get("author") or "",
            append_timestamp=cfg.append_timestamp,
            ext="txt",
        )
        out_path = self._output_dir / sanitize_filename(out_name)
        out_path.write_text(final_text, encoding="utf-8")
        logger.info(
            "Exported TXT (site=%s, book=%s): %s", self.site_key, book_id, out_path
        )
        return [out_path]

    def _export_chapter_txt(
        self: ExportTxtClientContext,
        book_id: str | None,
        chapter_id: str,
        cfg: ExporterConfig,
        *,
        stage: str | None = None,
        **kwargs: Any,
    ) -> Path | None:
        """Export a single chapter into a TXT file."""
        container_id = book_id or "global_chapters"
        raw_base = self._raw_data_dir / container_id
        if not raw_base.is_dir():
            return None

        # --- stage ---
        stage = stage or self._detect_latest_stage(container_id)

        # --- Load chapter ---
        dbfile = raw_base / f"chapter.{stage}.sqlite"
        if not dbfile.exists():
            return None

        with ChapterStorage(dbfile) as storage:
            chap = storage.get_chapter(chapter_id)

        if chap is None:
            return None

        chap_title = (chap.get("title") or f"Chapter {chapter_id}").strip()
        header = self._xp_txt_chapter_header(chap)
        final_text = header + self._xp_txt_chapter(chap, chap_title) + "\n"

        # --- Output file name ---
        out_name = format_filename(
            cfg.filename_template,
            title=chap_title,
            author="Unknown",
            append_timestamp=cfg.append_timestamp,
            ext="txt",
        )
        out_path = self._output_dir / sanitize_filename(out_name)
        out_path.write_text(final_text, encoding="utf-8")
        logger.info(
            "Exported TXT chapter (site=%s, book=%s, chapter=%s): %s",
            self.site_key,
            book_id,
            chapter_id,
            out_path,
        )
        return out_path

    def _xp_txt_header(self, book_info: BookInfoDict) -> str:
        """Top-of-file metadata block."""
        lines: list[str] = [book_info["book_name"].strip()]

        if author := book_info.get("author"):
            lines.append(f"作者：{author.strip()}")

        if serial_status := book_info.get("serial_status"):
            lines.append(f"状态：{serial_status.strip()}")

        if word_count := book_info.get("word_count"):
            lines.append(f"字数：{word_count.strip()}")

        if tags_list := book_info.get("tags"):
            tags = "、".join(t.strip() for t in tags_list if t)
            if tags:
                lines.append(f"标签：{tags}")

        if update_time := book_info.get("update_time"):
            lines.append(f"更新：{update_time.strip()}")

        if summary := book_info.get("summary"):
            lines.extend(["", summary.strip()])

        return "\n".join(lines)

    def _xp_txt_volume_header(self, vol_title: str, volume: VolumeInfoDict) -> str:
        """Render a volume heading. Include optional info if present."""
        meta_bits: list[str] = [f"=== {vol_title.strip()} ==="]

        if v_intro := volume.get("volume_intro"):
            meta_bits.append(f"简介：{v_intro.strip()}")

        return "\n".join(meta_bits)

    def _xp_txt_chapter_header(self, chap: ChapterDict) -> str:
        """Render a chapter heading."""
        return ""

    def _xp_txt_chapter(self, chap: ChapterDict, title_fallback: str) -> str:
        """Render one chapter to text"""
        # Title
        title_line = chap.get("title") or title_fallback

        body = chap["content"].strip()
        extras = chap.get("extra") or {}

        if not body and extras.get("resources"):
            return (
                f"{title_line}\n\n"
                "本章节包含纯图片内容, TXT 格式无法展示。\n"
                "请使用 EPUB 或 HTML 导出以查看完整章节。"
            )

        lines: list[str] = [title_line, body]

        if footer_txt := self._xp_txt_chapter_footer(chap):
            lines.append(footer_txt)

        return "\n\n".join(lines)

    def _xp_txt_missing_chapter(self, title: str) -> str:
        """Render a placeholder text block for missing or inaccessible chapters."""
        return f"{title}\n\n本章内容暂不可用"

    def _xp_txt_chapter_footer(self, chap: ChapterDict) -> str:
        """Render the footer block of a chapter.

        Subclasses may override this to append notes, author messages, etc.
        """
        return ""

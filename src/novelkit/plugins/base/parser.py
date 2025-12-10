"""
Abstract base class providing common behavior for site-specific parsers.
"""

from __future__ import annotations

import abc
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

from novelkit.schemas import (
    BookInfoDict,
    ChapterDict,
    ParserConfig,
    SearchResult,
)

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray
    from paddleocr import TextRecognition


class BaseParser(abc.ABC):
    """Base class defining the interface for extracting book metadata and chapter
    content from raw HTML. Subclasses provide site-specific parsing logic.
    """

    site_name: str
    site_key: str
    BASE_URL: str

    ADS: set[str] = set()

    _SPACE_RE = re.compile(r"\s+")
    _ZERO_WIDTH_RE = re.compile(r"[\u200B-\u200D\uFEFF]")
    _OCR_MODEL: TextRecognition | None = None

    def __init__(self, config: ParserConfig | None = None, **kwargs: Any) -> None:
        """Initialize the parser with a configuration object.

        Args:
            config: ParserConfig controlling parsing behavior and OCR settings.
        """
        config = config or ParserConfig()

        self._ocr_cfg = config.ocr_cfg
        self._enable_ocr = config.enable_ocr
        self._batch_size = config.batch_size
        self._use_truncation = config.use_truncation
        self._remove_watermark = config.remove_watermark
        self._cache_dir = Path(config.cache_dir) / self.site_name

        self._ad_pattern = self._compile_ads_pattern()

    @property
    def ocr_model(self) -> TextRecognition:
        """Lazy-load and return the shared OCR model instance.

        Returns:
            A PaddleOCR text recognition model instance.
        """
        if BaseParser._OCR_MODEL is None:
            from paddleocr import TextRecognition

            BaseParser._OCR_MODEL = TextRecognition(  # takes 5 ~ 12 sec to init
                model_name=self._ocr_cfg.model_name,
                model_dir=self._ocr_cfg.model_dir,
                input_shape=self._ocr_cfg.input_shape,
                device=self._ocr_cfg.device,
                precision=self._ocr_cfg.precision,
                cpu_threads=self._ocr_cfg.cpu_threads,
                enable_hpi=self._ocr_cfg.enable_hpi,
            )

        return BaseParser._OCR_MODEL

    @abc.abstractmethod
    def parse_book_info(
        self,
        raw_pages: list[str],
        book_id: str,
        **kwargs: Any,
    ) -> BookInfoDict:
        """Parses book-level metadata from raw page responses.

        Typically, the input comes from ``FetcherProtocol.fetch_book_info``.

        Args:
            raw_pages: A list of raw response texts (HTML or JSON) representing
                the book information pages. Multiple pages may be provided for
                multi-endpoint or paginated sites.
            book_id: Identifier of the book being parsed.
            **kwargs: Additional parser-specific parameters.

        Returns:
            Parsed book metadata extracted from ``raw_pages``.

        Raises:
            EmptyContent: The book information is intentionally empty.
            RestrictedContent: Access to book metadata is restricted.
        """
        ...

    @abc.abstractmethod
    def parse_chapter_content(
        self,
        raw_pages: list[str],
        chapter_id: str,
        book_id: str | None = None,
        **kwargs: Any,
    ) -> ChapterDict:
        """Parses chapter-level content from raw HTML, JSON, or text responses.

        Typically, the input comes from ``FetcherProtocol.fetch_chapter_content``.

        Args:
            raw_pages: A list of raw response texts representing a chapter's
                content sources. Some sites require HTML + AJAX JSON + metadata.
            chapter_id: Identifier of the chapter being parsed.
            book_id: Optional book identifier associated with the chapter.
            **kwargs: Additional parser-specific parameters.

        Returns:
            Parsed chapter content extracted from ``raw_pages``.

        Raises:
            EmptyContent: The chapter content is intentionally empty.
            RestrictedContent: Access to chapter is restricted.
        """
        ...

    def parse_search_result(
        self,
        raw_pages: list[str],
        limit: int | None = None,
        **kwargs: Any,
    ) -> list[SearchResult]:
        """Parse search-result entries from raw page responses.

        This method may stop early if ``limit`` is provided and enough results
        have been extracted.

        Args:
            raw_pages: A list of HTML or JSON responses for a search query.
            limit: Optional maximum number of results to return.
            **kwargs: Additional parser-specific keyword arguments.

        Returns:
            Extracted search result entries.

        Raises:
            NotImplementedError: If the parser does not support searching.
        """
        raise NotImplementedError(
            f"{self.site_name}: search is not supported on this site."
        )

    def _compile_ads_pattern(self) -> re.Pattern[str] | None:
        """Compile a regex pattern that matches advertisement text.

        Returns:
            The compiled pattern, or ``None`` if no ADS are configured.
        """
        if not self.ADS:
            return None

        return re.compile("|".join(self.ADS))

    def _is_ad_line(self, line: str) -> bool:
        """Check whether the text line matches any advertisement pattern.

        Args:
            line: A single line of text.

        Returns:
            True if the line matches any ad pattern, otherwise False.
        """
        return bool(self._ad_pattern and self._ad_pattern.search(line))

    @classmethod
    def _norm_space(cls, s: str, c: str = " ") -> str:
        """Collapse runs of whitespace (including full-width and newlines).

        Args:
            s: Input string to normalize.
            c: Replacement character for collapsed whitespace.

        Returns:
            Normalized string.
        """
        return cls._SPACE_RE.sub(c, s).strip()

    @classmethod
    def _clean_invisible(cls, s: str) -> str:
        """Remove zero-width characters."""
        return cls._ZERO_WIDTH_RE.sub("", s)

    @staticmethod
    def _first_str(xs: list[str], replaces: list[tuple[str, str]] | None = None) -> str:
        """Return the first non-empty string after applying replacements.

        Args:
            xs: List of raw strings.
            replaces: Optional list of (old, new) replacement pairs.

        Returns:
            Cleaned first string or empty string if unavailable.
        """
        replaces = replaces or []
        value: str = xs[0].strip() if xs else ""
        for old, new in replaces:
            value = value.replace(old, new)
        return value.strip()

    @staticmethod
    def _join_strs(xs: list[str], replaces: list[tuple[str, str]] | None = None) -> str:
        """Join multiple strings into a cleaned multiline value.

        Args:
            xs: List of raw strings.
            replaces: Optional list of (old, new) replacement pairs.

        Returns:
            Joined and normalized string.
        """
        replaces = replaces or []
        value = "\n".join(s.strip() for s in xs if s and s.strip())
        for old, new in replaces:
            value = value.replace(old, new)
        return value.strip()

    @classmethod
    def _abs_url(cls, url: str) -> str:
        """Convert a possibly relative URL into an absolute URL.

        Args:
            url: A URL string, possibly relative.

        Returns:
            An absolute URL resolved against ``BASE_URL``.
        """
        if url.startswith("//"):
            return "https:" + url
        return (
            url
            if url.startswith(("http://", "https://"))
            else urljoin(cls.BASE_URL, url)
        )

    def _extract_text_from_image(
        self,
        images: list[NDArray[np.uint8]],
        batch_size: int = 1,
    ) -> list[tuple[str, float]]:
        """Perform OCR on a list of images and extract recognized text.

        Args:
            images: A list of image arrays (np.ndarray) to process.
            batch_size: Number of images to process per inference batch.

        Returns:
            A list of ``(text, confidence_score)`` tuples for each image.
        """
        return [
            (pred.get("rec_text"), pred.get("rec_score"))
            for pred in self.ocr_model.predict(images, batch_size=batch_size)
        ]

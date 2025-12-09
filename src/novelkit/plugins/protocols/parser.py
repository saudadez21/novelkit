"""
Protocol definitions for parsing book metadata and chapter content.

This module defines :class:`ParserProtocol`, which transforms raw HTML or JSON
data retrieved by a fetcher into structured Python dictionaries.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

from novelkit.schemas import (
    BookInfoDict,
    ChapterDict,
    ParserConfig,
    SearchResult,
)

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray


class ParserProtocol(Protocol):
    """Protocol for a site-specific parser implementation.

    A parser converts raw HTML, JSON, or general text responses collected by a
    fetcher into structured Python dictionaries. These parsed outputs are then
    consumed by the client or downstream processing layers.
    """

    def __init__(self, config: ParserConfig | None = None, **kwargs: Any) -> None:
        """Initializes the parser.

        Args:
            config: Optional parser configuration object.
            **kwargs: Additional parser-specific initialization parameters.
        """
        ...

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
        """Parses search results from raw page responses.

        Args:
            raw_pages: A list of raw HTML/JSON response texts corresponding to
                search-result pages.
            limit: Optional maximum number of results to return. Parsing may
                stop early when the limit is reached.
            **kwargs: Additional parser-specific parameters.

        Returns:
            A list of ``SearchResult`` entries extracted from the raw pages.
        """
        ...


class _ParserContext(ParserProtocol, Protocol):
    """Internal protocol for shared parser mixin typing.

    This protocol defines common attributes and helper methods used by
    concrete parser classes and mixins. It is not intended to be used
    directly by external callers.
    """

    site_name: str
    site_key: str
    BASE_URL: str

    _cache_dir: Path
    _enable_ocr: bool
    _batch_size: int
    _use_truncation: bool  # Qidian config
    _remove_watermark: bool

    def _is_ad_line(self, line: str) -> bool:
        """Determines whether a text line contains advertisement content.

        Args:
            line: A single line of extracted or cleaned text.

        Returns:
            True if the line matches an ad pattern; otherwise False.
        """
        ...

    @classmethod
    def _norm_space(cls, s: str, c: str = " ") -> str:
        """Collapses runs of whitespace characters into a single replacement.

        Args:
            s: Input string to normalize.
            c: Replacement character used to collapse whitespace.

        Returns:
            A whitespace-normalized version of the input string.
        """
        ...

    @staticmethod
    def _first_str(
        xs: list[str],
        replaces: list[tuple[str, str]] | None = None,
    ) -> str:
        """Returns the first non-empty string from a list after replacements.

        Args:
            xs: A list of candidate strings.
            replaces: Optional ``(pattern, replacement)`` pairs applied.

        Returns:
            The first non-empty processed string, or an empty string if none match.
        """
        ...

    @staticmethod
    def _join_strs(
        xs: list[str],
        replaces: list[tuple[str, str]] | None = None,
    ) -> str:
        """Concatenates a list of strings with optional replacements.

        Args:
            xs: A list of strings to be concatenated.
            replaces: Optional ``(pattern, replacement)`` pairs applied.

        Returns:
            The concatenated string with all replacements applied.
        """
        ...

    @classmethod
    def _abs_url(cls, url: str) -> str:
        """Resolves a possibly relative URL into an absolute URL.

        Args:
            url: A URL string that may be relative or incomplete.

        Returns:
            An absolute URL resolved against ``BASE_URL``.
        """
        ...

    def _extract_text_from_image(
        self,
        images: list[NDArray[np.uint8]],
        batch_size: int = 1,
    ) -> list[tuple[str, float]]:
        """Runs OCR on image arrays and extracts recognized text.

        This method is typically used for sites where chapter content or metadata
        is embedded inside images (e.g., anti-piracy obfuscation or scanned pages).

        Args:
            images: A list of ``np.ndarray`` image arrays (H x W x C).
            batch_size: Number of images per OCR inference batch. Must be >= 1.

        Returns:
            A list of ``(text, confidence_score)`` tuples extracted from the images.
        """
        ...

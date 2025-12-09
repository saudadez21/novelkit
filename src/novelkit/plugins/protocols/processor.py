"""
Protocols for text processors used to transform book and chapter data.

This module defines :class:`ProcessorProtocol`, which specifies the
interface for components that modify, normalize, or enrich structured
metadata and chapter content.
"""

from typing import Any, Protocol

from novelkit.schemas import BookInfoDict, ChapterDict


class ProcessorProtocol(Protocol):
    """Protocol for processors that transform book metadata or chapter content.

    A processor operates on structured data dictionaries and may apply cleanup,
    normalization, formatting, enrichment, or other transformations depending
    on the implementation. The returned objects should preserve the overall
    schema of the input.
    """

    def __init__(self, config: dict[str, Any], **kwargs: Any) -> None:
        """Initializes the processor.

        Args:
            config: A dictionary containing processor-specific configuration
                values.
            **kwargs: Additional initialization parameters.
        """
        ...

    def process_book_info(self, book_info: BookInfoDict) -> BookInfoDict:
        """Processes and transforms book-level metadata.

        Implementations may modify fields such as titles, authors, tags,
        descriptions, or any other metadata that benefits from normalization
        or enrichment.

        Args:
            book_info: The structured book metadata.

        Returns:
            The transformed or original book metadata.
        """
        ...

    def process_chapter(self, chapter: ChapterDict) -> ChapterDict:
        """Processes and transforms a single chapter.

        Implementations may apply text cleanup, formatting adjustments,
        language conversion, annotation insertion, or other transformations
        depending on the processor's purpose.

        Args:
            chapter: The structured chapter dictionary.

        Returns:
            The transformed or original chapter data.
        """
        ...

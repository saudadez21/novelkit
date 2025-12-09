"""
Protocol definitions for client implementations.

A client coordinates interactions with site-specific fetchers and parsers,
and provides high-level operations such as retrieving metadata, downloading
chapters, running processors, caching media, and exporting content.
"""

import types
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Protocol, Self

from novelkit.schemas import (
    BookConfig,
    BookInfoDict,
    ChapterDict,
    ExporterConfig,
    PipelineMeta,
    ProcessorConfig,
    SearchResult,
    VolumeInfoDict,
)

from .fetcher import FetcherProtocol
from .parser import ParserProtocol
from .ui import (
    DownloadUI,
    ExportUI,
    LoginUI,
    ProcessUI,
)


class ClientProtocol(Protocol):
    """Protocol for a site-specific client implementation.

    A client serves as the high-level interface for retrieving, transforming,
    and exporting book-related data. It manages the fetcher, parser, media
    handling, and optional processing or exporting steps. Implementations
    typically subclass ``BaseClient`` or provide compatible behavior.
    """

    site_key: str
    r18: bool
    support_search: bool

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    async def init(self) -> None:
        """Initializes the client and its internal components."""
        ...

    async def close(self) -> None:
        """Releases network sessions, background workers, and other resources."""
        ...

    async def login(
        self,
        *,
        username: str = "",
        password: str = "",
        cookies: dict[str, str] | None = None,
        attempt: int = 1,
        **kwargs: Any,
    ) -> bool:
        """Attempts asynchronous authentication.

        Args:
            username: Username or account identifier.
            password: Account password.
            cookies: Optional cookie mapping to restore a previous session.
            attempt: Retry counter for multi-step or recursive login logic.

        Returns:
            True if login succeeds; otherwise False.
        """
        ...

    async def login_with_ui(
        self,
        *,
        ui: LoginUI,
        login_cfg: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> bool:
        """Performs asynchronous authentication using the configured UI handler.

        Args:
            ui: Login interaction handler.
            login_cfg: Optional credential or cookie mapping.
            **kwargs: Additional client-specific parameters.

        Returns:
            True if authentication succeeds; otherwise False.
        """
        ...

    async def logout(self) -> None:
        """Logs out from the current session if supported by the platform."""
        ...

    async def get_book_info(
        self,
        book_id: str,
        **kwargs: Any,
    ) -> BookInfoDict:
        """Fetch and parse metadata for a given book.

        Attempts to load metadata from cache unless outdated or disabled.

        Args:
            book_id: Identifier of the book.
            **kwargs: Additional parameters.

        Returns:
            Structured book metadata.
        """
        ...

    async def get_chapter(
        self,
        chapter_id: str,
        book_id: str | None = None,
        **kwargs: Any,
    ) -> ChapterDict | None:
        """Retrieves parsed content for a chapter.

        Implementations may perform fetching, parsing, and retry handling.

        Args:
            chapter_id: Chapter identifier.
            book_id: Optional book identifier.
            **kwargs: Additional parameters.

        Returns:
            Parsed chapter content, or None if unavailable.
        """
        ...

    async def search(
        self,
        keyword: str,
        *,
        limit: int | None = None,
        **kwargs: Any,
    ) -> list[SearchResult]:
        """Searches for books matching the given keyword.

        Args:
            keyword: Search query string.
            limit: Optional maximum number of results.
            **kwargs: Additional parameters.

        Returns:
            A list of matching search results.
        """
        ...

    async def download_book(
        self,
        book: BookConfig | str,
        *,
        ui: DownloadUI | None = None,
        **kwargs: Any,
    ) -> None:
        """Downloads metadata and chapter content for a book.

        Args:
            book: Book configuration or identifier.
            ui: Optional progress reporter.
            **kwargs: Additional parameters.
        """
        ...

    async def download_chapter(
        self,
        chapter_id: str,
        book_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Downloads a specific chapter.

        Args:
            chapter_id: Chapter identifier.
            book_id: Optional book identifier.
            **kwargs: Additional parameters.
        """
        ...

    async def cache_media(
        self,
        book: BookConfig | str,
        *,
        force_update: bool = False,
        concurrent: int = 10,
        **kwargs: Any,
    ) -> None:
        """Fetches and caches media referenced by a book.

        Args:
            book: Book configuration or identifier.
            force_update: Redownload media even if cached.
            concurrent: Maximum number of parallel download tasks.
            **kwargs: Additional parameters.
        """
        ...

    def process_book(
        self,
        book: BookConfig | str,
        processors: list[ProcessorConfig],
        *,
        ui: ProcessUI | None = None,
        **kwargs: Any,
    ) -> None:
        """Applies one or more processors to a book.

        Args:
            book: Book configuration or identifier.
            processors: Processor definitions to apply.
            ui: Optional UI callbacks.
            **kwargs: Additional parameters.
        """
        ...

    def export_book(
        self,
        book: BookConfig | str,
        cfg: ExporterConfig | None = None,
        *,
        formats: list[str] | None = None,
        stage: str | None = None,
        ui: ExportUI | None = None,
        **kwargs: Any,
    ) -> dict[str, list[Path]]:
        """Exports a book to one or more output formats.

        Args:
            book: Book configuration or identifier.
            cfg: Optional exporter configuration.
            formats: Output formats to generate.
            stage: Optional processing stage to export from.
            ui: Optional export progress handler.

        Returns:
            A mapping of format -> list of generated file paths.
        """
        ...

    def export_chapter(
        self,
        chapter_id: str,
        book_id: str | None = None,
        cfg: ExporterConfig | None = None,
        *,
        formats: list[str] | None = None,
        stage: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Path | None]:
        """Exports a single chapter to one or more formats.

        Args:
            chapter_id: Chapter identifier.
            book_id: Optional book identifier.
            cfg: Optional exporter configuration.
            formats: Output formats to generate.
            stage: Optional export stage.

        Returns:
            A mapping of format -> exported file path or None on failure.
        """
        ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        tb: types.TracebackType | None,
    ) -> None: ...


class _ClientContext(ClientProtocol, Protocol):
    """Internal protocol for shared client mixin typing.

    Provides common fields and helpers used by client implementations.
    """

    fetcher: FetcherProtocol
    parser: ParserProtocol

    _cache_dir: Path
    _raw_data_dir: Path
    _output_dir: Path
    _debug_dir: Path

    _request_interval: float
    _retry_times: int
    _backoff_factor: float

    _cache_book_info: bool
    _cache_chapter: bool
    _fetch_inaccessible: bool

    _storage_batch_size: int

    @property
    def workers(self) -> int:
        """Returns the number of worker threads or tasks."""
        ...

    async def _sleep(self, interval: float | None = None) -> None:
        """Sleeps for a fixed interval between sequential requests."""
        ...

    def _normalize_book(self, book: BookConfig | str) -> BookConfig:
        """Normalize a book input into a ``BookConfig`` instance.

        Converts supported input types into a ``BookConfig`` object. Unsupported
        types will result in a ``TypeError``.

        Args:
            book: A value representing a book configuration or identifier.

        Returns:
            A ``BookConfig`` instance corresponding to the given input.

        Raises:
            TypeError: If ``book`` is not a supported type.
        """
        ...

    def _book_dir(self, book_id: str) -> Path:
        """Returns the directory containing a book's stored data."""
        ...

    def _detect_latest_stage(self, book_id: str) -> str:
        """Determines the latest available processing stage for export.

        Strategy:
          * If ``pipeline.json`` exists, walk pipeline metadata in reverse
            order and select the last stage whose SQLite output exists.
          * Fallback: any recorded stage with a valid SQLite file.
          * Otherwise return ``"raw"``.
        """
        ...

    def _load_book_info(self, book_id: str, stage: str = "raw") -> BookInfoDict:
        """Loads and returns book metadata for the given stage."""
        ...

    def _save_book_info(
        self,
        book_id: str,
        book_info: BookInfoDict,
        stage: str = "raw",
    ) -> None:
        """Serializes and stores ``BookInfoDict`` as JSON."""
        ...

    def _load_pipeline_meta(self, book_id: str) -> PipelineMeta:
        """Loads pipeline metadata for the book."""
        ...

    def _save_pipeline_meta(self, book_id: str, meta: PipelineMeta) -> None:
        """Writes pipeline metadata to ``pipeline.json``."""
        ...

    def _save_raw_pages(
        self,
        filename: str,
        raw_pages: list[str],
        *,
        book_id: str | None = None,
        folder: str = "raw",
    ) -> None:
        """Optionally persists raw fetched page fragments.

        Files are named ``{book_id}_{filename}_{index}.html`` and stored
        under the given folder.
        """
        ...

    @staticmethod
    def _filter_volumes(
        vols: list[VolumeInfoDict],
        start_id: str | None,
        end_id: str | None,
        ignore: frozenset[str],
    ) -> list[VolumeInfoDict]:
        """Filters volumes to include only chapters within the given ranges."""
        ...

    def _iter_volume_chapters(
        self,
        raw_base: Path,
        stage: str,
        vols: list[VolumeInfoDict],
    ) -> Iterator[tuple[int, VolumeInfoDict, dict[str, ChapterDict | None]]]:
        """Iterate through volume chapters."""
        ...

    def _extract_chapter_ids(
        self,
        vols: list[VolumeInfoDict],
        start_id: str | None,
        end_id: str | None,
        ignore: frozenset[str],
    ) -> list[str]:
        """Returns a list of chapter IDs matching range and exclusion filters."""
        ...

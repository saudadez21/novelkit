from __future__ import annotations

import asyncio
import json
import logging
import types
from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, Self, cast

from novelkit.infra.persistence.chapter_storage import ChapterStorage
from novelkit.infra.sessions import BaseSession
from novelkit.plugins.mixins import (
    DownloadMixin,
    ExportTxtMixin,
    ProcessMixin,
)
from novelkit.plugins.registry import hub
from novelkit.schemas import (
    BookConfig,
    BookInfoDict,
    ChapterDict,
    ChapterInfoDict,
    ClientConfig,
    ExporterConfig,
    PipelineMeta,
    SearchResult,
    VolumeInfoDict,
)

if TYPE_CHECKING:
    from novelkit.plugins.protocols.ui import (
        ExportUI,
        LoginUI,
    )

logger = logging.getLogger(__name__)


class _ExportBookFunc(Protocol):
    def __call__(
        self,
        book: BookConfig,
        cfg: ExporterConfig,
        *,
        stage: str | None,
        **kwargs: Any,
    ) -> list[Path]: ...


class _ExportChapterFunc(Protocol):
    def __call__(
        self,
        book_id: str | None,
        chapter_id: str,
        cfg: ExporterConfig,
        *,
        stage: str | None,
        **kwargs: Any,
    ) -> Path | None: ...


class BaseClient(
    DownloadMixin,
    ExportTxtMixin,
    ProcessMixin,
):
    site_key: str
    r18: bool
    support_search: bool

    def __init__(
        self,
        config: ClientConfig | None = None,
        *,
        session: BaseSession | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the downloader for a specific site.

        Args:
            config: Downloader configuration settings. If not provided, a default
                `ClientConfig` instance is created.
            session: Optional session instance to use for network requests.
            **kwargs: Additional keyword arguments for subclasses.
        """
        cfg = config or ClientConfig()

        self._save_html = cfg.save_html
        self._cache_book_info = cfg.cache_book_info
        self._cache_chapter = cfg.cache_chapter
        self._fetch_inaccessible = cfg.fetch_inaccessible

        self._request_interval = cfg.request_interval
        self._retry_times = cfg.retry_times
        self._backoff_factor = cfg.backoff_factor
        self._workers = max(1, cfg.workers)
        self._storage_batch_size = max(1, cfg.storage_batch_size)

        self.fetcher = hub.build_fetcher(
            self.site_key, cfg.fetcher_cfg, session=session
        )
        self.parser = hub.build_parser(self.site_key, cfg.parser_cfg)

        self._raw_data_dir = Path(cfg.raw_data_dir) / self.site_key
        self._cache_dir = Path(cfg.cache_dir) / self.site_key
        self._output_dir = Path(cfg.output_dir)
        self._debug_dir = Path.cwd() / "debug" / self.site_key

    async def init(self) -> None:
        """Initialize underlying resources."""
        await self.fetcher.init()

    async def close(self) -> None:
        """Close underlying resources."""
        if self.fetcher.is_logged_in:
            await self.fetcher.save_state(self._cache_dir)
        await self.fetcher.close()

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
        return await self.fetcher.login(
            username=username,
            password=password,
            cookies=cookies,
            attempt=attempt,
            **kwargs,
        )

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
        if await self.fetcher.load_state(self._cache_dir):
            return True

        login_data = await ui.prompt(self.fetcher.login_fields, prefill=login_cfg)
        if not await self.fetcher.login(**login_data):
            if ui:
                ui.on_login_failed()
            return False

        await self.fetcher.save_state(self._cache_dir)
        if ui:
            ui.on_login_success()
        return True

    async def logout(self) -> None:
        """Logs out from the current session if supported by the platform."""
        await self.fetcher.logout()

    async def search(
        self,
        keyword: str,
        *,
        limit: int | None = None,
        **kwargs: Any,
    ) -> list[SearchResult]:
        """Search for books matching the keyword.

        Args:
            keyword: Search query string.
            limit: Optional maximum number of results to return.
            **kwargs: Additional parameters.

        Returns:
            A list of `SearchResult` objects.
        """
        raw_pages = await self.fetcher.fetch_search_result(keyword, **kwargs)
        return self.parser.parse_search_result(raw_pages, limit=limit, **kwargs)

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
            formats: Output formats to generate (e.x. `["epub", "txt"]`).
            stage: Optional processing stage to export from (e.x. `"raw"`, `"cleaner"`).
            ui: Optional export progress handler.
            **kwargs: Additional keyword arguments for concrete implementations.

        Returns:
            A mapping from format name to lists of generated file paths.
        """
        book = self._normalize_book(book)
        cfg = cfg or ExporterConfig()
        formats = formats or ["epub"]
        results: dict[str, list[Path]] = {}

        for fmt in formats:
            method_name = f"_export_{cfg.split_mode}_{fmt.lower()}"
            export_func: _ExportBookFunc | None = getattr(self, method_name, None)

            if not callable(export_func):
                if ui:
                    ui.on_unsupported(book, fmt)
                results[fmt] = []
                continue

            if ui:
                ui.on_start(book, fmt)

            try:
                paths = export_func(book, cfg, stage=stage, **kwargs)
                results[fmt] = paths

                if paths and ui:
                    for path in paths:
                        ui.on_success(book, fmt, path)

            except Exception as e:
                results[fmt] = []
                logger.warning(f"Error exporting {fmt}: {e}")
                if ui:
                    ui.on_error(book, fmt, e)

        return results

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
        """Persist a single chapter to disk in one or more formats.

        Args:
            chapter_id: Identifier of the chapter to export.
            book_id: Optional identifier of the book.
            cfg: Optional `ExporterConfig` defining export parameters.
            formats: List of formats such as ``["txt"]``.
            stage: Optional export stage name used for multi-phase exports.
            **kwargs: Additional keyword arguments for concrete implementations.

        Returns:
            A mapping from format name to the generated file path, or None if
            export for a given format failed or was skipped.
        """
        cfg = cfg or ExporterConfig()
        formats = formats or ["txt"]
        results: dict[str, Path | None] = {}

        for fmt in formats:
            method_name = f"_export_chapter_{fmt.lower()}"
            export_func: _ExportChapterFunc | None = getattr(self, method_name, None)

            if not callable(export_func):
                logger.warning("Unsupported chapter export format '%s'", fmt)
                results[fmt] = None
                continue

            try:
                path = export_func(
                    book_id=book_id,
                    chapter_id=chapter_id,
                    cfg=cfg,
                    stage=stage,
                    **kwargs,
                )
                results[fmt] = path

            except Exception as e:
                results[fmt] = None
                logger.warning(
                    "Error exporting chapter (format=%s): %s",
                    fmt,
                    e,
                )

        return results

    @property
    def workers(self) -> int:
        """Number of worker threads or tasks used for concurrent operations."""
        return self._workers

    async def _sleep(self, interval: float | None = None) -> None:
        """Sleeps for a fixed interval between sequential requests."""
        actual = self._request_interval if interval is None else interval

        if actual > 0:
            await asyncio.sleep(actual)

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
        if isinstance(book, BookConfig):
            return book
        if isinstance(book, str):
            return BookConfig(book_id=book)
        raise TypeError(f"Invalid book type: {type(book)!r}")

    def _book_dir(self, book_id: str) -> Path:
        """Return the base directory for raw data of a given book.

        Args:
            book_id: Book identifier.

        Returns:
            Path to the book's raw data directory.
        """
        return self._raw_data_dir / book_id

    def _save_book_info(
        self, book_id: str, book_info: BookInfoDict, stage: str = "raw"
    ) -> None:
        """Serialize and save the book metadata as JSON.

        Args:
            book_id: Identifier of the book.
            book_info: Dictionary containing metadata about the book.
            stage: Pipeline stage name used in the metadata filename
        """
        base = self._book_dir(book_id)
        base.mkdir(parents=True, exist_ok=True)
        (base / f"book_info.{stage}.json").write_text(
            json.dumps(book_info, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_book_info(self, book_id: str, stage: str = "raw") -> BookInfoDict:
        """Load and return the book metadata for the given book.

        Args:
            book_id: Book identifier.
            stage: Pipeline stage name used in the metadata filename.

        Returns:
            Parsed `BookInfoDict` containing metadata about the book.

        Raises:
            FileNotFoundError: If the metadata file does not exist.
            ValueError: If the JSON is invalid or has an unexpected structure.
        """
        base = self._book_dir(book_id)
        info_path = base / f"book_info.{stage}.json"

        if not info_path.is_file():
            raise FileNotFoundError(f"Missing metadata file: {info_path}")

        try:
            data = json.loads(info_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"Corrupt JSON in {info_path}: {e}") from e

        if not isinstance(data, dict):
            raise ValueError(
                f"Invalid JSON structure in {info_path}: expected an object at the top"
            )

        return cast(BookInfoDict, data)

    def _load_pipeline_meta(self, book_id: str) -> PipelineMeta:
        """Load and return the pipeline metadata for the given book.

        The method attempts to read and parse `pipeline.json` stored under the
        book's directory. If the file is missing, unreadable, or contains
        unexpected structures, a default empty metadata payload is returned.

        Args:
            book_id: Book identifier.

        Returns:
            A `PipelineMeta` dictionary with ``pipeline`` and ``executed`` keys.
        """
        base = self._book_dir(book_id)
        meta_path = base / "pipeline.json"

        if not meta_path.is_file():
            return {"pipeline": [], "executed": {}}

        try:
            raw = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return {"pipeline": [], "executed": {}}

        pipeline = raw.get("pipeline", [])
        if not isinstance(pipeline, list):
            pipeline = []

        executed = raw.get("executed", {})
        if not isinstance(executed, dict):
            executed = {}

        return cast(
            PipelineMeta,
            {
                "pipeline": pipeline,
                "executed": executed,
            },
        )

    def _save_pipeline_meta(self, book_id: str, meta: PipelineMeta) -> None:
        """Serialize and write `pipeline.json` for the given book.

        Args:
            book_id: Book identifier.
            meta: Pipeline metadata containing ``pipeline`` and ``executed`` keys.
        """
        base = self._book_dir(book_id)
        base.mkdir(parents=True, exist_ok=True)
        (base / "pipeline.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _save_raw_pages(
        self,
        filename: str,
        raw_pages: list[str],
        *,
        book_id: str | None = None,
        folder: str = "raw",
    ) -> None:
        """Save HTML snippets for debugging if HTML saving is enabled.

        Filenames follow the pattern `{book_id}_{filename}_{index}.html` and
        are stored under the specified folder. If book_id is None, the
        filename becomes `{filename}_{index}.html`.

        Args:
            book_id: Book identifier.
            filename: Filename prefix used when writing individual pages.
            raw_pages: List of HTML strings to save.
            folder: Subdirectory name under the debug directory where files are
                stored.
        """
        if not self._save_html:
            return
        html_dir = self._debug_dir / folder
        html_dir.mkdir(parents=True, exist_ok=True)
        prefix = filename if book_id is None else f"{book_id}_{filename}"
        for i, html in enumerate(raw_pages):
            (html_dir / f"{prefix}_{i}.html").write_text(html, encoding="utf-8")

    def _extract_chapter_ids(
        self,
        vols: list[VolumeInfoDict],
        start_id: str | None,
        end_id: str | None,
        ignore: frozenset[str],
    ) -> list[str]:
        """Extract chapter IDs from volume metadata within an optional range.

        Args:
            vols: List of volume dictionaries containing chapter information.
            start_id: Inclusive start chapter ID, or None to start from the
                first chapter.
            end_id: Inclusive end chapter ID, or None to go until the last
                chapter.
            ignore: Set of chapter IDs that should always be excluded.

        Returns:
            A list of chapter IDs respecting the specified range and ignore set.
        """
        seen_start = start_id is None
        out: list[str] = []
        for vol in vols:
            for chap in vol["chapters"]:
                cid = chap.get("chapterId")
                if not cid:
                    continue
                if not seen_start:
                    if cid == start_id:
                        seen_start = True
                    else:
                        continue
                if cid not in ignore:
                    accessible = chap.get("accessible", True)
                    if accessible or self._fetch_inaccessible:
                        out.append(cid)
                if end_id is not None and cid == end_id:
                    return out
        return out

    @staticmethod
    def _filter_volumes(
        vols: list[VolumeInfoDict],
        start_id: str | None,
        end_id: str | None,
        ignore: frozenset[str],
    ) -> list[VolumeInfoDict]:
        """Filter volume metadata to include only selected chapter ranges.

        Rebuilds volumes to include only chapters within the
        `[start_id, end_id]` range (inclusive), while excluding any chapter
        IDs present in `ignore`.

        Args:
            vols: List of volume dictionaries.
            start_id: Inclusive start chapter ID, or None to start from the
                first available chapter.
            end_id: Inclusive end chapter ID, or None to include chapters
                until the end.
            ignore: Set of chapter IDs to exclude regardless of range.

        Returns:
            A new list of volumes with chapters filtered accordingly. Volumes
            with no remaining chapters are omitted.
        """
        if start_id is None and end_id is None and not ignore:
            return vols

        started = start_id is None
        finished = False
        result: list[VolumeInfoDict] = []

        for vol in vols:
            if finished:
                break

            kept: list[ChapterInfoDict] = []

            for ch in vol.get("chapters", []):
                cid = ch.get("chapterId")
                if not cid:
                    continue

                # wait until hit the start_id
                if not started:
                    if cid == start_id:
                        started = True
                    else:
                        continue

                if cid not in ignore:
                    kept.append(ch)

                # check for end_id after keeping
                if end_id is not None and cid == end_id:
                    finished = True
                    break

            if kept:
                result.append(
                    {
                        **vol,
                        "chapters": kept,
                    }
                )

        return result

    def _iter_volume_chapters(
        self,
        raw_base: Path,
        stage: str,
        vols: list[VolumeInfoDict],
    ) -> Iterator[tuple[int, VolumeInfoDict, dict[str, ChapterDict | None]]]:
        """Iterate through volume chapters.

        Args:
            raw_base (Path): Path containing the raw book data.
            stage (str): Data stage identifier (e.g., `"raw"`).
            vols (list[VolumeInfoDict]): List of volume info dictionaries.

        Yields:
            tuple: (v_idx, vol, chap_map) where chap_map maps chapterId to chapter data.
        """
        db_path = raw_base / f"chapter.{stage}.sqlite"
        with ChapterStorage(db_path) as storage:
            for v_idx, vol in enumerate(vols, start=1):
                chapters = vol.get("chapters", [])
                cids = [c["chapterId"] for c in chapters if c.get("chapterId")]
                chap_map = storage.get_chapters(cids) if cids else {}

                yield v_idx, vol, chap_map

    def _detect_latest_stage(self, book_id: str) -> str:
        """Detect the latest available processing stage for a book.

        Strategy:
            * If ``pipeline.json`` exists, walk the pipeline list in reverse
              and pick the last stage whose associated SQLite and book info
              files both exist.
            * Fallback: any executed record with an existing SQLite file.
            * Else: return `"raw"`.

        Args:
            book_id: Book identifier.

        Returns:
            The chosen stage name (for example, `"raw"`, `"cleaner"`).
        """
        base = self._book_dir(book_id)
        meta = self._load_pipeline_meta(book_id)

        for stg in reversed(meta["pipeline"]):
            db_file = base / f"chapter.{stg}.sqlite"
            info_file = base / f"book_info.{stg}.json"
            if db_file.is_file() and info_file.is_file():
                return stg

        return "raw"

    async def __aenter__(self) -> Self:
        await self.init()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        tb: types.TracebackType | None,
    ) -> None:
        await self.close()


class CommonClient(BaseClient):
    """
    Client for unsupported or generic novel sites.
    """

    def __init__(
        self,
        site_key: str,
        config: ClientConfig | None = None,
        *,
        session: BaseSession | None = None,
        **kwargs: Any,
    ) -> None:
        self.site_key = site_key
        super().__init__(config, session=session, **kwargs)

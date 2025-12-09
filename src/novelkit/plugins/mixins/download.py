from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Protocol, final

from novelkit.infra.http_defaults import DEFAULT_HEADERS, MEDIA_ACCEPT_MAP
from novelkit.infra.persistence.chapter_storage import ChapterStorage
from novelkit.libs.filesystem import url_to_hashed_name
from novelkit.plugins.base.errors import EmptyContent, RestrictedContent
from novelkit.schemas import (
    BookConfig,
    BookInfoDict,
    ChapterDict,
    MediaResource,
    MediaType,
)

ONE_DAY = 86400  # seconds
logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from novelkit.plugins.protocols import (
        DownloadUI,
        _ClientContext,
    )

    class DownloadClientContext(_ClientContext, Protocol):
        """"""

        MEDIA_BASE_HEADERS: dict[str, str]

        async def _dl_fix_chapter_ids(
            self,
            book_id: str,
            book_info: BookInfoDict,
            storage: ChapterStorage,
        ) -> BookInfoDict: ...

        def _dl_check_refetch(self, chap: ChapterDict) -> bool: ...

        async def _dl_fetch_binary_file(
            self,
            url: str,
            target_dir: Path,
            *,
            name: str | None = None,
            force_update: bool = False,
            media_type: MediaType | None = None,
        ) -> str: ...

        async def _dl_fetch_media_resources(
            self,
            resources: list[MediaResource],
            media_dir: Path,
            *,
            force_update: bool = False,
            concurrent: int = 5,
        ) -> None: ...


@final
class StopToken:
    """Typed sentinel used to end queues."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "STOP"


STOP: Final[StopToken] = StopToken()


class DownloadMixin:
    """"""

    MEDIA_BASE_HEADERS = DEFAULT_HEADERS

    async def download_book(
        self: DownloadClientContext,
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
        book = self._normalize_book(book)
        book_id = book.book_id

        raw_base = self._raw_data_dir / book_id
        raw_base.mkdir(parents=True, exist_ok=True)
        db_path = raw_base / "chapter.raw.sqlite"

        if ui:
            await ui.on_start(book)

        # ---- metadata ---
        book_info = await self.get_book_info(book_id=book_id)
        with ChapterStorage(db_path) as storage:
            book_info = await self._dl_fix_chapter_ids(
                book_id,
                book_info,
                storage,
            )

            plan = self._extract_chapter_ids(
                book_info["volumes"],
                book.start_id,
                book.end_id,
                book.ignore_ids,
            )
            if not plan:
                logger.info(
                    "Nothing to do after filtering (site=%s, book=%s)",
                    self.site_key,
                    book_id,
                )
                return

            total = len(plan)
            done = 0

            async def bump(n: int = 1) -> None:
                nonlocal done
                done += n
                if ui:
                    await ui.on_progress(done, total)

            # ---- queues & batching ---
            save_q: asyncio.Queue[ChapterDict | StopToken] = asyncio.Queue(maxsize=10)
            batches: dict[bool, list[ChapterDict]] = {False: [], True: []}
            sem = asyncio.Semaphore(self.workers)

            def _batch(need_refetch: bool) -> list[ChapterDict]:
                return batches[need_refetch]

            async def flush_batch(need_refetch: bool) -> None:
                batch = _batch(need_refetch)
                if not batch:
                    return
                try:
                    storage.upsert_chapters(batch, need_refetch=need_refetch)
                except Exception as e:
                    logger.error(
                        "Storage batch upsert failed (site=%s, book=%s): %s",
                        self.site_key,
                        book_id,
                        e,
                    )
                else:
                    await bump(len(batch))
                finally:
                    batch.clear()

            async def flush_all() -> None:
                await flush_batch(False)
                await flush_batch(True)

            # ---- workers ---
            async def storage_worker() -> None:
                while True:
                    item = await save_q.get()
                    if isinstance(item, StopToken):
                        break

                    need = self._dl_check_refetch(item)
                    bucket = _batch(need)
                    bucket.append(item)
                    if len(bucket) >= self._storage_batch_size:
                        await flush_batch(need)
                await flush_all()

            async def producer(cid: str) -> None:
                async with sem:
                    if self._cache_chapter and not storage.need_refetch(cid):
                        await bump(1)
                        return

                    chap = await self.get_chapter(book_id=book_id, chapter_id=cid)
                    if chap is not None:
                        await save_q.put(chap)

                    await self._sleep()

            # ---- run tasks ---
            storage_task = asyncio.create_task(storage_worker())

            try:
                tasks = [asyncio.create_task(producer(cid)) for cid in plan]
                await asyncio.gather(*tasks)

                # signal storage to finish and wait for flush
                await save_q.put(STOP)
                await storage_task
            except asyncio.CancelledError:
                logger.info("Download cancelled, stopping storage worker...")
                await save_q.put(STOP)

                try:
                    await asyncio.wait_for(storage_task, timeout=10)
                except TimeoutError:
                    logger.warning("Storage worker did not exit, cancelling.")
                    storage_task.cancel()
                    await asyncio.gather(storage_task, return_exceptions=True)

                raise
            finally:
                if not storage_task.done():
                    storage_task.cancel()
                    await asyncio.gather(storage_task, return_exceptions=True)

        # ---- done ---
        await self.cache_media(book)
        if ui:
            await ui.on_complete(book)

        logger.info(
            "Download completed for site=%s book=%s",
            self.site_key,
            book_id,
        )

    async def download_chapter(
        self: DownloadClientContext,
        chapter_id: str,
        book_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Download a single chapter, with or without a book context.

        If ``book_id`` is provided, the chapter is stored under that book's
        raw-data directory. If ``book_id`` is ``None``, the chapter is treated
        as a standalone chapter and stored under the shared ``global_chapters``
        directory.

        Args:
            chapter_id: Identifier of the chapter to download.
            book_id: Optional book identifier. Use ``None`` for standalone chapters.
        """
        container_id = book_id or "global_chapters"
        raw_base = self._raw_data_dir / container_id
        raw_base.mkdir(parents=True, exist_ok=True)
        media_dir = raw_base / "media"
        db_path = raw_base / "chapter.raw.sqlite"

        # ---- fetch chapter ----
        chap = await self.get_chapter(book_id=book_id, chapter_id=chapter_id)
        if chap is None:
            logger.warning(
                "Chapter fetch returned None (site=%s, book=%s, chapter=%s)",
                self.site_key,
                book_id,
                chapter_id,
            )
            return

        resources = chap["extra"].get("resources")
        if resources:
            await self._dl_fetch_media_resources(
                resources,
                media_dir,
                force_update=False,
            )

        # ---- save directly ----
        with ChapterStorage(db_path) as storage:
            storage.upsert_chapter(
                chap,
                need_refetch=self._dl_check_refetch(chap),
            )

        logger.info(
            "Single chapter downloaded (site=%s, book=%s, chapter=%s)",
            self.site_key,
            book_id,
            chapter_id,
        )

    async def cache_media(
        self: DownloadClientContext,
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
        book = self._normalize_book(book)
        book_id = book.book_id

        raw_base = self._raw_data_dir / book_id
        raw_base.mkdir(parents=True, exist_ok=True)
        media_dir = raw_base / "media"
        db_path = raw_base / "chapter.raw.sqlite"

        book_info = self._load_book_info(book_id=book_id)

        if cover_url := book_info.get("cover_url"):
            await self._dl_fetch_binary_file(
                cover_url,
                media_dir,
                name="cover",
                force_update=force_update,
                media_type="image",
            )

        for v in book_info.get("volumes", []):
            if vol_cover := v.get("volume_cover"):
                await self._dl_fetch_binary_file(
                    vol_cover,
                    media_dir,
                    force_update=force_update,
                    media_type="image",
                )

        plan = self._extract_chapter_ids(
            book_info["volumes"], book.start_id, book.end_id, book.ignore_ids
        )
        if not plan:
            logger.info(
                "Nothing to do after filtering (site=%s, book=%s)",
                self.site_key,
                book_id,
            )
            return

        with ChapterStorage(db_path) as storage:
            chapters = storage.get_chapters(plan)
            for chap in chapters.values():
                if chap is None:
                    continue

                resources = chap["extra"].get("resources")
                if resources:
                    await self._dl_fetch_media_resources(
                        resources,
                        media_dir,
                        force_update=force_update,
                        concurrent=concurrent,
                    )

    async def get_book_info(
        self: DownloadClientContext,
        book_id: str,
        **kwargs: Any,
    ) -> BookInfoDict:
        """Fetch and parse metadata for a given book.

        Attempts to load metadata from cache unless outdated or disabled.

        Args:
            book_id: Unique identifier of the book.

        Returns:
            Parsed book metadata as a BookInfoDict.
        """
        book_info: BookInfoDict | None = None
        if self._cache_book_info:
            try:
                book_info = self._load_book_info(book_id)
                age = time.time() - book_info.get("last_checked", 0.0)
                if age < ONE_DAY:
                    return book_info
            except FileNotFoundError:
                logger.debug("No cached metadata for %s", book_id)
            except Exception as exc:
                logger.info("Failed to load cached metadata for %s: %s", book_id, exc)

        info_html = await self.fetcher.fetch_book_info(book_id)
        self._save_raw_pages("info", info_html, book_id=book_id)

        book_info = self.parser.parse_book_info(info_html, book_id)
        book_info["last_checked"] = time.time()
        self._save_book_info(book_id, book_info)
        return book_info

    async def get_chapter(
        self: DownloadClientContext,
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
        for attempt in range(self._retry_times + 1):
            try:
                raw_pages = await self.fetcher.fetch_chapter_content(
                    book_id=book_id, chapter_id=chapter_id
                )
                self._save_raw_pages(chapter_id, raw_pages, book_id=book_id)

                chap = await asyncio.to_thread(
                    self.parser.parse_chapter_content,
                    raw_pages,
                    book_id=book_id,
                    chapter_id=chapter_id,
                )

                return chap

            except EmptyContent as exc:
                logger.warning(
                    "Empty content (site=%s, book=%s, chapter=%s): %s",
                    self.site_key,
                    book_id,
                    chapter_id,
                    exc,
                )
                return None

            except RestrictedContent as exc:
                logger.warning(
                    "Restricted chapter (site=%s, book=%s, chapter=%s): %s",
                    self.site_key,
                    book_id,
                    chapter_id,
                    exc,
                )
                return None

            except Exception as e:
                if attempt < self._retry_times:
                    logger.info(
                        "Retrying (site=%s, book=%s, chapter=%s, attempt=%d): %s",
                        self.site_key,
                        book_id,
                        chapter_id,
                        attempt + 1,
                        e,
                    )
                    await self._sleep(interval=self._backoff_factor * (2**attempt))
                else:
                    logger.warning(
                        "Failed chapter (site=%s, book=%s, chapter=%s): %s",
                        self.site_key,
                        book_id,
                        chapter_id,
                        e,
                    )
        return None

    async def _dl_fix_chapter_ids(
        self: DownloadClientContext,
        book_id: str,
        book_info: BookInfoDict,
        storage: ChapterStorage,
    ) -> BookInfoDict:
        """Repair missing `chapterId` fields in book metadata.

        Missing chapter IDs are inferred by loading the previous chapter
        and reading its `extra.next_cid` field. Refetched chapters are saved
        into the provided storage.

        Args:
            book_id: Unique identifier of the book.
            book_info: Metadata structure containing volume/chapter listing.
            storage: ChapterStorage instance for reading and caching chapters.

        Returns:
            Updated book_info with repaired chapter IDs.
        """
        prev_cid: str = ""
        for vol in book_info["volumes"]:
            for chap in vol["chapters"]:
                cid = chap.get("chapterId")
                if cid:
                    prev_cid = cid
                    continue

                if not prev_cid:
                    continue

                # missing id: try storage
                data = storage.get_chapter(prev_cid)
                if not data:
                    # fetch+parse previous to discover next
                    data = await self.get_chapter(book_id, prev_cid)
                    if not data:
                        continue
                    storage.upsert_chapter(data)
                    await self._sleep()

                next_cid = data.get("extra", {}).get("next_cid")
                if not next_cid:
                    logger.warning(
                        "No next_cid (site=%s, book=%s, prev=%s)",
                        self.site_key,
                        book_id,
                        prev_cid,
                    )
                    continue

                logger.info(
                    "Repaired chapterId (site=%s, book=%s): %s <- %s",
                    self.site_key,
                    book_id,
                    next_cid,
                    prev_cid,
                )
                chap["chapterId"] = next_cid
                prev_cid = next_cid

        self._save_book_info(book_id, book_info)
        return book_info

    def _dl_check_refetch(self, chap: ChapterDict) -> bool:
        """Determine whether a chapter should be refetched.

        Args:
            chap: Parsed chapter dictionary.

        Returns:
            True if the chapter requires refetching, False otherwise.
        """
        return False

    async def _dl_fetch_binary_file(
        self: DownloadClientContext,
        url: str,
        target_dir: Path,
        *,
        name: str | None = None,
        force_update: bool = False,
        media_type: MediaType | None = None,
    ) -> str:
        """Fetch a binary resource from a URL and store it under a hashed filename.

        This helper downloads arbitrary binary content (images, fonts, stylesheets,
        attachments, etc.) and writes it to ``target_dir`` using a deterministic
        hashed filename derived from the URL.

        Args:
            url: Remote URL of the binary content to download.
            target_dir: Directory where the file will be stored.
            name: Optional custom base name used for hashing.
            force_update: Redownload even if a cached file already exists.

        Returns:
            The hashed filename used for the stored file.
        """
        hashed = url_to_hashed_name(url, name=name)
        path = target_dir / hashed
        if path.exists() and not force_update:
            return hashed

        headers = self.MEDIA_BASE_HEADERS.copy()
        if media_type:
            accept = MEDIA_ACCEPT_MAP.get(media_type)
            if accept:
                headers["Accept"] = accept

        try:
            content = await self.fetcher.fetch_binary(url)
        except Exception as exc:
            logger.warning("Failed media fetch url=%s: %s", url, exc)
            return hashed

        target_dir.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        logger.debug("Saved media %s -> %s", url, path)
        return hashed

    async def _dl_fetch_media_resources(
        self: DownloadClientContext,
        resources: list[MediaResource],
        media_dir: Path,
        *,
        force_update: bool = False,
        concurrent: int = 5,
    ) -> None:
        """Download all media resources for a chapter."""
        sem = asyncio.Semaphore(concurrent)

        async def worker(res: MediaResource) -> None:
            url = res.get("url")
            if not url:
                return
            mtype = res.get("type", "other")
            async with sem:
                await self._dl_fetch_binary_file(
                    url,
                    media_dir,
                    force_update=force_update,
                    media_type=mtype,
                )

        tasks = [worker(r) for r in resources]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

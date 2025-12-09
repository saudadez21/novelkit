"""
Base fetcher implementations for site plugins.

This module defines :class:`BaseFetcher` and :class:`GenericFetcher`, which
provide shared HTTP session handling, rate limiting, pagination helpers.
"""

from __future__ import annotations

import abc
import asyncio
import logging
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, Self
from urllib.parse import quote_plus, urljoin

from novelkit.infra.sessions import BaseSession, create_session
from novelkit.plugins.utils.rate_limiter import TokenBucketRateLimiter
from novelkit.schemas import FetcherConfig, LoginField

logger = logging.getLogger(__name__)


class BaseFetcher(abc.ABC):
    """Base class for site-specific fetchers.

    ``BaseFetcher`` manages the underlying HTTP session, retry behavior,
    rate limiting, login state, and convenience helpers for retrieving
    textual or binary resources. Site implementors should subclass this
    class and provide implementations for the content-fetching methods.
    """

    site_name: str
    site_key: str

    BASE_URL: str

    def __init__(
        self,
        config: FetcherConfig | None = None,
        *,
        session: BaseSession | None = None,
        **kwargs: Any,
    ) -> None:
        """Initializes a new fetcher instance.

        Args:
            config: Optional fetcher configuration. If omitted, a default
                :class:`FetcherConfig` instance is created.
            session: Optional preconfigured HTTP session. If omitted, a new
                session is created via :func:`create_session`.
            **kwargs: Additional keyword arguments forwarded to
                :func:`create_session` when ``session`` is not provided.
        """
        config = config or FetcherConfig()

        self._locale_style = config.locale_style
        self._request_interval = config.request_interval
        self._is_logged_in = False

        self.session = session or create_session(
            backend=config.backend,
            cfg=config.session_cfg,
            **kwargs,
        )

        self._rate_limiter: TokenBucketRateLimiter | None = (
            TokenBucketRateLimiter(config.max_rps) if config.max_rps > 0 else None
        )

    @property
    def is_logged_in(self) -> bool:
        """Whether the fetcher is currently authenticated.

        Returns:
            True if an authenticated session is active; otherwise False.
        """
        return self._is_logged_in

    @property
    def login_fields(self) -> list[LoginField]:
        """Describes the fields required for interactive login.

        Returns:
            A list of :class:`LoginField` instances describing required
                credential input. The default implementation requests a single
                cookie field for cookie-based authentication.
        """
        return [
            LoginField(
                name="cookies",
                label="Cookie",
                type="cookie",
                required=True,
                placeholder="Paste your login cookies here",
                description="Copy the cookies from your browser's developer tools while logged in.",  # noqa: E501
            ),
        ]

    async def init(
        self,
        **kwargs: Any,
    ) -> None:
        """Initializes underlying resources for the fetcher.

        Delegates to the underlying session's initialization logic.

        Args:
            **kwargs: Additional keyword arguments forwarded to
                :meth:`BaseSession.init`.
        """
        await self.session.init()

    async def close(self) -> None:
        """Closes the underlying session and releases associated resources."""
        await self.session.close()

    async def login(
        self,
        username: str = "",
        password: str = "",
        cookies: dict[str, str] | None = None,
        attempt: int = 1,
        **kwargs: Any,
    ) -> bool:
        """Attempts to establish an authenticated session.

        The default implementation only supports cookie-based login. If no
        cookies are provided, the method immediately returns ``False``.

        Args:
            username: Username for login. Ignored by the default implementation.
            password: Password for login. Ignored by the default implementation.
            cookies: Optional cookie mapping to inject into the session.
            attempt: Current login attempt count, used by subclasses that
                implement multi-step login flows.
            **kwargs: Additional parameters reserved for subclass extensions.

        Returns:
            True if the fetcher considers the session authenticated.
        """
        if not cookies:
            return False
        self.session.update_cookies(cookies)

        self._is_logged_in = await self.check_login_status()
        return self._is_logged_in

    async def logout(self) -> None:
        """Logs out from the current session if supported by the platform.

        This method clears session cookies and resets authentication state.
        Subclasses may override to call site-specific logout endpoints.
        """
        self.session.clear_cookies()
        self._is_logged_in = False

    async def check_login_status(self) -> bool:
        """Checks whether the current session remains authenticated.

        The default implementation always returns ``True``. Subclasses should
        override this method in order to perform real authentication checks
        against the target platform.

        Returns:
            True if the session is considered authenticated.
        """
        return True

    @abc.abstractmethod
    async def fetch_book_info(
        self,
        book_id: str,
        **kwargs: Any,
    ) -> list[str]:
        """Fetches raw pages containing book metadata.

        Args:
            book_id: Identifier of the book on the target site.
            **kwargs: Additional parameters forwarded to lower-level routines.

        Returns:
            A list of response bodies representing book information pages.
        """
        ...

    @abc.abstractmethod
    async def fetch_chapter_content(
        self,
        chapter_id: str,
        book_id: str | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """Fetches raw content for a single chapter.

        Args:
            chapter_id: Identifier of the chapter.
            book_id: Optional book identifier required by some sites.
            **kwargs: Additional parameters forwarded to lower-level routines.

        Returns:
            A list of response bodies representing the chapter content.
        """
        ...

    async def fetch_search_result(
        self,
        keyword: str,
        **kwargs: Any,
    ) -> list[str]:
        """Fetches raw search result pages for a given keyword.

        The default implementation raises :class:`NotImplementedError`.
        Subclasses that support search functionality should override this
        method.

        Args:
            keyword: Search query string.
            **kwargs: Additional parameters forwarded to lower-level routines.

        Returns:
            A list of response bodies representing search result pages.

        Raises:
            NotImplementedError: If the site does not support search.
        """
        raise NotImplementedError(
            f"{self.site_name}: search is not supported on this site."
        )

    async def fetch_text(
        self,
        url: str,
        encoding: str = "utf-8",
        **kwargs: Any,
    ) -> str:
        """Fetches and decodes textual content from the given URL.

        This method performs an asynchronous HTTP GET request. If rate limiting
        is enabled, the request may be delayed before transmission. The response
        body is decoded using the specified encoding; implementations may apply
        fallback encodings internally.

        Args:
            url: Target URL to fetch.
            encoding: Preferred character encoding for decoding the body text.
            **kwargs: Additional parameters forwarded to ``BaseSession.get``.

        Returns:
            The decoded textual content.

        Raises:
            RuntimeError: If the fetcher or session is not initialized.
            ConnectionError: If the request fails, times out, or returns a
                non-successful HTTP status.
        """
        if self._rate_limiter:
            await self._rate_limiter.wait()

        resp = await self.session.get(url, encoding=encoding, **kwargs)
        if not resp.ok:
            raise ConnectionError(f"Request to {url} failed with status {resp.status}")
        return resp.text

    async def fetch_binary(
        self,
        url: str,
        **kwargs: Any,
    ) -> bytes:
        """Fetches raw binary content from the given URL.

        This method performs an asynchronous HTTP GET request and returns the
        response body as raw bytes. It is suitable for downloading images,
        fonts, or other binary media. Rate limiting is applied when enabled.

        Args:
            url: Target URL to fetch.
            **kwargs: Additional parameters forwarded to ``BaseSession.get``.

        Returns:
            The binary response body.

        Raises:
            RuntimeError: If the fetcher or session is not initialized.
            ConnectionError: If the request fails, times out, or returns a
                non-successful HTTP status.
        """
        if self._rate_limiter:
            await self._rate_limiter.wait()

        resp = await self.session.get(url, **kwargs)
        if not resp.ok:
            raise ConnectionError(f"Request to {url} failed with status {resp.status}")
        return resp.content

    async def load_state(self, state_dir: Path) -> bool:
        """Restores session state from persistent storage.

        Implementations may reload cookies, tokens, or internal fetcher state.

        Returns:
            True if state restoration succeeds; otherwise False.
        """
        return self.session.load_cookies(state_dir)

    async def save_state(self, state_dir: Path) -> bool:
        """Persists the current session state.

        Implementations may save cookies, tokens, or fetcher metadata.

        Returns:
            True if state persistence succeeds; otherwise False.
        """
        return self.session.save_cookies(state_dir)

    async def _sleep(self) -> None:
        """Sleeps for a fixed interval between sequential requests.

        This helper is intended for subclasses that must introduce additional
        delays between specific requests, such as multi-page fetch sequences
        or rate-sensitive endpoints.
        """
        if self._request_interval > 0:
            await asyncio.sleep(self._request_interval)

    @staticmethod
    def _quote(q: str, encoding: str | None = None, errors: str | None = None) -> str:
        """URL-encode a query string safely."""
        return quote_plus(q, encoding=encoding, errors=errors)

    @staticmethod
    def _build_url(base: str, params: dict[str, str]) -> str:
        """Builds a URL with query parameters."""
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{base}?{query_string}"

    @classmethod
    def _abs_url(cls, url: str) -> str:
        """Converts a possibly relative URL into an absolute URL."""
        if url.startswith("//"):
            return "https:" + url
        return (
            url
            if url.startswith(("http://", "https://"))
            else urljoin(cls.BASE_URL, url)
        )

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


class GenericFetcher(BaseFetcher):
    """Generic mid-level fetcher for common novel site patterns.

    ``GenericFetcher`` implements a configurable pattern that covers the
    majority of sites:

    * Single-page or paginated book-info pages.
    * Optional separate catalog (table-of-contents) pages.
    * Single-page or paginated chapter content pages.
    * Optional transformation rules for book/chapter identifiers.
    * Optional requirement for a ``book_id`` when fetching chapters.
    """

    INFO_BASE_URL: str | None = None
    INFO_BASE_URL_MAP: dict[str, str] = {}
    CATALOG_BASE_URL: str | None = None
    CATALOG_BASE_URL_MAP: dict[str, str] = {}
    CHAPTER_BASE_URL: str | None = None
    CHAPTER_BASE_URL_MAP: dict[str, str] = {}

    # -------------------------------
    # ID transformation rules
    # -------------------------------
    BOOK_ID_REPLACEMENTS: list[tuple[str, str]] = []
    CHAP_ID_REPLACEMENTS: list[tuple[str, str]] = []

    # -------------------------------
    # URL templates (relative paths)
    # Example: "/book/index/{book_id}"
    # -------------------------------
    BOOK_INFO_PATH: str | None = None
    BOOK_CATALOG_PATH: str | None = None
    CHAPTER_PATH: str | None = None

    # --------------------------------------
    # Paging / structure flags
    # --------------------------------------
    USE_PAGINATED_INFO: bool = False
    USE_PAGINATED_CATALOG: bool = False
    USE_PAGINATED_CHAPTER: bool = False

    HAS_SEPARATE_CATALOG: bool = False

    # --------------------------------------
    # book_id requirement handling
    # --------------------------------------
    REQUIRE_BOOK_ID: bool = True

    def __init__(
        self,
        config: FetcherConfig | None = None,
        *,
        session: BaseSession | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(config, session=session, **kwargs)
        self._info_base = self._pick_base_url(
            locale_style=self._locale_style,
            base_url_map=self.INFO_BASE_URL_MAP,
            base_url=self.INFO_BASE_URL,
        )
        self._catalog_base = self._pick_base_url(
            locale_style=self._locale_style,
            base_url_map=self.CATALOG_BASE_URL_MAP,
            base_url=self.CATALOG_BASE_URL,
        )
        self._chapter_base = self._pick_base_url(
            locale_style=self._locale_style,
            base_url_map=self.CHAPTER_BASE_URL_MAP,
            base_url=self.CHAPTER_BASE_URL,
        )

    async def fetch_book_info(self, book_id: str, **kwargs: Any) -> list[str]:
        """Fetches book info and optional catalog pages.

        Depending on the configured flags, this may fetch a single info
        page, multiple paginated info pages, and optionally a separate
        catalog (table-of-contents) page or its paginated variant.

        Args:
            book_id: Identifier of the book on the target site.
            **kwargs: Additional keyword arguments forwarded to
                :meth:`BaseFetcher.fetch`.

        Returns:
            A list of raw response bodies for info and catalog pages.

        Raises:
            NotImplementedError: If :attr:`BOOK_INFO_PATH` (or
                :attr:`BOOK_CATALOG_PATH` when required) is not defined.
        """
        if not self.BOOK_INFO_PATH:
            raise NotImplementedError(
                f"{self.site_name}: BOOK_INFO_PATH must be defined."
            )

        # Transform book id if needed
        book_id = self._transform_book_id(book_id)
        pages: list[str] = []

        # ---------- 1) Book Info ----------
        if self.USE_PAGINATED_INFO:
            pages = await self._paginate(
                make_suffix=lambda idx: self.relative_info_url(book_id, idx),
                page_type="info",
                book_id=book_id,
                **kwargs,
            )
            if not pages:
                return []
        else:
            url = self._info_base + self.BOOK_INFO_PATH.format(book_id=book_id)
            pages = [await self.fetch_text(url, **kwargs)]

        # ---------- 2) Catalog ----------
        if self.HAS_SEPARATE_CATALOG:
            if not self.BOOK_CATALOG_PATH:
                raise NotImplementedError(
                    f"{self.site_name}: BOOK_CATALOG_PATH must be defined."
                )

            if self.USE_PAGINATED_CATALOG:
                catalog_pages = await self._paginate(
                    make_suffix=lambda idx: self.relative_catalog_url(book_id, idx),
                    page_type="catalog",
                    book_id=book_id,
                    **kwargs,
                )
                if not catalog_pages:
                    return []
                pages.extend(catalog_pages)

            else:
                catalog_url = self._catalog_base + self.BOOK_CATALOG_PATH.format(
                    book_id=book_id
                )
                pages.append(await self.fetch_text(catalog_url, **kwargs))

        return pages

    async def fetch_chapter_content(
        self,
        chapter_id: str,
        book_id: str | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """Fetches chapter content pages for a single chapter.

        This handles both single-page and paginated chapter structures.
        For sites that require a ``book_id`` to address chapter content,
        :attr:`REQUIRE_BOOK_ID` should be set to True.

        Args:
            chapter_id: Identifier of the chapter.
            book_id: Optional book identifier. Required if
                :attr:`REQUIRE_BOOK_ID` is True.
            **kwargs: Additional keyword arguments forwarded to
                :meth:`BaseFetcher.fetch`.

        Returns:
            A list of raw response bodies representing the chapter content.

        Raises:
            ValueError: If :attr:`REQUIRE_BOOK_ID` is True but ``book_id``
                is not provided.
            NotImplementedError: If :attr:`CHAPTER_PATH` is not defined.
        """
        if self.REQUIRE_BOOK_ID and not book_id:
            raise ValueError(
                f"{self.site_name}: book_id is required for chapter fetch, "
                f"but got book_id={book_id!r}."
            )

        # Transform IDs
        chapter_id = self._transform_chap_id(chapter_id)
        book_id = self._transform_book_id(book_id) if book_id else None

        if not self.CHAPTER_PATH:
            raise NotImplementedError(f"{self.site_name}: CHAPTER_PATH must be set.")

        # ---------- Paginated Chapters ----------
        if self.USE_PAGINATED_CHAPTER:
            return await self._paginate(
                make_suffix=lambda idx: self.relative_chapter_url(
                    book_id, chapter_id, idx
                ),
                page_type="chapter",
                book_id=book_id,
                chapter_id=chapter_id,
                **kwargs,
            )

        # ---------- Single Chapter ----------
        url = self._chapter_base + self.CHAPTER_PATH.format(
            book_id=book_id, chapter_id=chapter_id
        )
        return [await self.fetch_text(url, **kwargs)]

    @classmethod
    def relative_info_url(cls, book_id: str, idx: int) -> str:
        """Builds the relative URL suffix for an info page.

        This is used only when :attr:`USE_PAGINATED_INFO` is True.

        Args:
            book_id: Identifier of the book.
            idx: Page index starting from 1.

        Returns:
            A relative path beginning with ``"/"``.

        Raises:
            NotImplementedError: If the subclass does not override this
                method.
        """
        raise NotImplementedError(f"{cls.__name__} must implement relative_info_url")

    @classmethod
    def relative_catalog_url(cls, book_id: str, idx: int) -> str:
        """Builds the relative URL suffix for a catalog page.

        This is used only when :attr:`USE_PAGINATED_CATALOG` is True.

        Args:
            book_id: Identifier of the book.
            idx: Page index starting from 1.

        Returns:
            A relative path beginning with ``"/"``.

        Raises:
            NotImplementedError: If the subclass does not override this
                method.
        """
        raise NotImplementedError(f"{cls.__name__} must implement relative_catalog_url")

    @classmethod
    def relative_chapter_url(
        cls, book_id: str | None, chapter_id: str, idx: int
    ) -> str:
        """Builds the relative URL suffix for a chapter page.

        This is used only when :attr:`USE_PAGINATED_CHAPTER` is True.

        Args:
            book_id: Optional identifier of the book. Some sites may not
                require this value for addressing chapter pages.
            chapter_id: Identifier of the chapter.
            idx: Page index starting from 1.

        Returns:
            A relative path beginning with ``"/"``.

        Raises:
            NotImplementedError: If the subclass does not override this
                method.
        """
        raise NotImplementedError(f"{cls.__name__} must implement relative_chapter_url")

    def should_continue_pagination(
        self,
        current_html: str,
        next_suffix: str,
        next_idx: int,
        page_type: Literal["info", "catalog", "chapter"],
        book_id: str | None,
        chapter_id: str | None = None,
    ) -> bool:
        """Determines whether the pagination loop should continue.

        The default implementation continues as long as the ``next_suffix``
        appears in the current HTML. Subclasses may override this to use
        more sophisticated logic (e.g., checking a "next" link or specific
        markers).

        Args:
            current_html: HTML contents of the current page.
            next_suffix: Relative URL suffix that will be requested next.
            next_idx: Index of the next page.
            page_type: Logical type of the paginated content (``"info"``,
                ``"catalog"``, or ``"chapter"``).
            book_id: Optional book identifier associated with the request.
            chapter_id: Optional chapter identifier associated with the
                request.

        Returns:
            True if another page should be fetched; otherwise False.
        """
        return next_suffix in current_html

    def _pick_base_url(
        self,
        locale_style: str,
        base_url_map: dict[str, str],
        base_url: str | None = None,
    ) -> str:
        """Resolves the effective base URL for the given locale style.

        The locale style is normalized to lower case and mapped via
        `base_url_map`. If there is no entry for the style, the
        default :attr:`BASE_URL` is used.

        Args:
            locale_style: Locale or region style key from the configuration.

        Returns:
            The base URL that should be used for this fetcher instance.
        """
        key = locale_style.strip().lower()
        return base_url_map.get(key, base_url) or self.BASE_URL

    def _transform_book_id(self, book_id: str) -> str:
        """Applies configured replacement rules to a book identifier.

        Args:
            book_id: Original book identifier.

        Returns:
            The transformed book identifier after applying all configured
            replacements.
        """
        for old, new in self.BOOK_ID_REPLACEMENTS:
            book_id = book_id.replace(old, new)
        return book_id

    def _transform_chap_id(self, chap_id: str) -> str:
        """Applies configured replacement rules to a chapter identifier.

        Args:
            chap_id: Original chapter identifier.

        Returns:
            The transformed chapter identifier after applying all configured
            replacements.
        """
        for old, new in self.CHAP_ID_REPLACEMENTS:
            chap_id = chap_id.replace(old, new)
        return chap_id

    async def _paginate(
        self,
        *,
        make_suffix: Callable[[int], str],
        page_type: Literal["info", "catalog", "chapter"],
        book_id: str | None = None,
        chapter_id: str | None = None,
        **fetch_kwargs: Any,
    ) -> list[str]:
        """Generic pagination loop for info/catalog/chapter pages.

        This helper repeatedly fetches pages derived from ``make_suffix``,
        starting at index 1, and stops when
        :meth:`should_continue_pagination` returns False.

        Args:
            make_suffix: Callable that produces a relative path suffix for
                a given page index (starting at 1).
            page_type: Logical type of the paginated content (``"info"``,
                ``"catalog"``, or ``"chapter"``).
            book_id: Optional book identifier associated with the request.
            chapter_id: Optional chapter identifier associated with the
                request.
            **fetch_kwargs: Additional keyword arguments forwarded to
                :meth:`BaseFetcher.fetch`.

        Returns:
            A list of raw response bodies for all paginated pages.

        Raises:
            RuntimeError: If :attr:`BASE_URL` is not defined.
        """
        origin = self.BASE_URL
        if page_type == "info":
            origin = self._info_base
        elif page_type == "catalog":
            origin = self._catalog_base
        elif page_type == "chapter":
            origin = self._chapter_base

        if not origin:
            raise RuntimeError(
                f"{self.site_name}: BASE_URL is required for {page_type}"
            )

        pages: list[str] = []
        idx = 1
        suffix = make_suffix(idx)

        while True:
            html = await self.fetch_text(origin + suffix, **fetch_kwargs)
            pages.append(html)
            idx += 1
            suffix = make_suffix(idx)
            if not self.should_continue_pagination(
                current_html=html,
                next_suffix=suffix,
                next_idx=idx,
                page_type=page_type,
                book_id=book_id,
                chapter_id=chapter_id,
            ):
                break
            await self._sleep()

        return pages

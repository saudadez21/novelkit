"""
Protocol definitions for asynchronous fetchers used to communicate with
novel platforms.

This module defines :class:`FetcherProtocol`, which abstracts network
operations such as authentication, metadata retrieval, chapter fetching,
and media downloading for site-specific implementations.
"""

import types
from pathlib import Path
from typing import Any, Protocol, Self

from novelkit.infra.sessions import BaseSession
from novelkit.schemas import FetcherConfig, LoginField


class FetcherProtocol(Protocol):
    """Protocol for an asynchronous network fetcher.

    Implementations of this protocol handle HTTP requests, login
    management, cache restoration, and downloading both textual and
    binary resources.
    """

    site_name: str
    site_key: str

    def __init__(
        self,
        config: FetcherConfig | None = None,
        *,
        session: BaseSession | None = None,
        **kwargs: Any,
    ) -> None: ...

    async def init(self) -> None:
        """Performs asynchronous initialization.

        Typical responsibilities include setting up the network session,
        applying proxy or connection settings, or restoring persisted state.

        This method must be called before any fetch operation.
        """
        ...

    async def close(self) -> None:
        """Closes network and file resources gracefully.

        Implementations should terminate all active sessions and release
        internal caches.
        """
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

        Implementations may support multiple login methods, such as
        credential-based login, cookie reuse, or multi-step authentication.

        Args:
            username: Username or account identifier.
            password: Account password.
            cookies: Optional cookie mapping to restore a previous session.
            attempt: Retry counter for multi-step or recursive login logic.

        Returns:
            True if login succeeds; otherwise False.
        """
        ...

    async def logout(self) -> None:
        """Logs out from the current session if supported by the platform.

        Implementations may clear authentication cookies, invalidate tokens,
        or call a site-specific logout endpoint.
        """
        ...

    @property
    def is_logged_in(self) -> bool:
        """Indicates whether the fetcher is currently authenticated.

        Returns:
            True if an authenticated session is active.
        """
        ...

    @property
    def login_fields(self) -> list[LoginField]:
        """Returns the fields required for interactive or programmatic login.

        Returns:
            A list of ``LoginField`` objects describing required credential fields.
        """
        ...

    async def check_login_status(self) -> bool:
        """Verifies whether the current session is still authenticated.

        This method performs a lightweight, asynchronous check to determine
        whether the session remains valid. Implementations may rely on
        site-specific endpoints, cookie presence, token validation, or other
        heuristics depending on the platform.

        Returns:
            True if the session is still considered authenticated.
        """
        ...

    async def fetch_book_info(
        self,
        book_id: str,
        **kwargs: Any,
    ) -> list[str]:
        """Fetches the raw HTML or JSON content of a book information page.

        Args:
            book_id: Identifier of the book on the target site.

        Returns:
            A list of strings representing raw page responses.
        """
        ...

    async def fetch_chapter_content(
        self,
        chapter_id: str,
        book_id: str | None = None,
        **kwargs: Any,
    ) -> list[str]:
        """Fetches raw HTML or JSON content for a single chapter.

        Args:
            chapter_id: Identifier of the chapter.
            book_id: Book identifier, if required by the platform.

        Returns:
            A list of strings representing the raw chapter content.
        """
        ...

    async def fetch_search_result(
        self,
        keyword: str,
        **kwargs: Any,
    ) -> list[str]:
        """Fetches raw search results for the given keyword.

        Args:
            keyword: Search query string.

        Returns:
            A list of strings representing search result pages or API responses.
        """
        ...

    async def fetch_text(
        self,
        url: str,
        encoding: str = "utf-8",
        **kwargs: Any,
    ) -> str:
        """Fetches and decodes textual content from the given URL.

        This method performs an asynchronous HTTP GET request using the underlying
        session object. If rate limiting is enabled, the request will be delayed
        according to the configured throttling rules. The response body is decoded
        using the specified character encoding.

        Args:
            url: Target URL to fetch.
            encoding: Character encoding used to decode the response body.
            **kwargs: Additional keyword arguments forwarded to :meth:`BaseSession.get`.

        Returns:
            The decoded text content if the request succeeds

        Raises:
            RuntimeError: If the fetcher has not been initialized.
            ConnectionError: Times out, or returns a non-successful HTTP status.
        """
        ...

    async def fetch_binary(
        self,
        url: str,
        **kwargs: Any,
    ) -> bytes:
        """Fetches raw binary content from the given URL.

        This method performs an asynchronous HTTP GET request and returns the
        unmodified response body as a byte sequence. It is intended for downloading
        images, fonts, media files, or any other non-text resource. Rate limiting
        will be enforced when applicable.

        Args:
            url: Target URL to fetch.
            **kwargs: Additional keyword arguments forwarded to :meth:`BaseSession.get`.

        Returns:
            The raw binary content if the request succeeds

        Raises:
            RuntimeError: If called before the fetcher is initialized.
            ConnectionError: Times out, or returns a non-successful HTTP status.
        """
        ...

    async def load_state(self, state_dir: Path) -> bool:
        """Restores session state from persistent storage.

        This allows restoring cookies or authentication tokens from previous
        runs without requiring the user to log in again.

        Returns:
            True if the state was successfully restored; otherwise False.
        """
        ...

    async def save_state(self, state_dir: Path) -> bool:
        """Persists the current session state.

        State may include cookies, authentication tokens, or additional fetcher
        information necessary to resume the session later.

        Returns:
            True if the state was saved successfully; otherwise False.
        """
        ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        tb: types.TracebackType | None,
    ) -> None: ...

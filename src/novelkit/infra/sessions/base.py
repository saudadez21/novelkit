from __future__ import annotations

import abc
import types
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Self, TypedDict, Unpack

from novelkit.infra.http_defaults import DEFAULT_USER_HEADERS
from novelkit.schemas import SessionConfig

from .response import BaseResponse


class BaseRequestKwargs(TypedDict, total=False):
    headers: Mapping[str, str] | Sequence[tuple[str, str]]
    cookies: dict[str, str] | list[tuple[str, str]]


class GetRequestKwargs(BaseRequestKwargs, total=False):
    params: dict[str, Any] | list[tuple[str, Any]] | None


class PostRequestKwargs(BaseRequestKwargs, total=False):
    params: dict[str, Any] | list[tuple[str, Any]] | None
    data: Any
    json: Any


class BaseSession(abc.ABC):
    def __init__(self, cfg: SessionConfig | None = None, **kwargs: Any) -> None:
        """Initializes the session using the provided configuration.

        Args:
            cfg: Optional configuration object defining session behavior.
            **kwargs: Additional parameters reserved for backend-specific
                initialization.
        """
        cfg = cfg or SessionConfig()

        self._timeout = cfg.timeout
        self._max_connections = cfg.max_connections
        self._verify_ssl = cfg.verify_ssl
        self._impersonate = cfg.impersonate
        self._http2 = cfg.http2
        self._proxy = cfg.proxy
        self._proxy_user = cfg.proxy_user
        self._proxy_pass = cfg.proxy_pass
        self._trust_env = cfg.trust_env
        self._cookies = cfg.cookies or {}
        self._session: Any = None

        self._headers = (
            cfg.headers.copy()
            if cfg.headers is not None
            else DEFAULT_USER_HEADERS.copy()
        )
        if cfg.user_agent:
            self._headers["User-Agent"] = cfg.user_agent

    @abc.abstractmethod
    async def init(
        self,
        **kwargs: Any,
    ) -> None:
        """Initializes backend-specific resources.

        Args:
            **kwargs: Additional parameters required by backend implementations.
        """
        ...

    @abc.abstractmethod
    async def close(self) -> None:
        """Releases and cleans up any allocated resources."""
        ...

    @abc.abstractmethod
    async def get(
        self,
        url: str,
        *,
        allow_redirects: bool | None = None,
        verify: bool | None = None,
        encoding: str = "utf-8",
        **kwargs: Unpack[GetRequestKwargs],
    ) -> BaseResponse:
        """Performs an HTTP GET request.

        Args:
            url: Target URL.
            allow_redirects: Whether redirects should be allowed.
            verify: Whether SSL verification should be performed.
            encoding: Response text encoding.
            **kwargs: Additional request parameters forwarded to the backend.

        Returns:
            BaseResponse: A response wrapper for the GET request.

        Raises:
            RuntimeError: If the session has not been initialized.
        """
        ...

    @abc.abstractmethod
    async def post(
        self,
        url: str,
        *,
        allow_redirects: bool | None = None,
        verify: bool | None = None,
        encoding: str = "utf-8",
        **kwargs: Unpack[PostRequestKwargs],
    ) -> BaseResponse:
        """Performs an HTTP POST request.

        Args:
            url: Target URL.
            allow_redirects: Whether redirects should be allowed.
            verify: Whether SSL verification should be performed.
            encoding: Response text encoding.
            **kwargs: Additional request parameters forwarded to the backend.

        Returns:
            BaseResponse: A response wrapper for the POST request.

        Raises:
            RuntimeError: If the session has not been initialized.
        """
        ...

    @abc.abstractmethod
    def load_cookies(self, cookies_dir: Path, filename: str | None = None) -> bool:
        """Loads cookies from a JSON file.

        Args:
            cookies_dir: Directory where cookie files are stored.
            filename: Optional specific filename to load.

        Returns:
            bool: True if cookies were loaded successfully, otherwise False.
        """
        ...

    @abc.abstractmethod
    def save_cookies(self, cookies_dir: Path, filename: str | None = None) -> bool:
        """Saves cookies to a JSON file.

        Args:
            cookies_dir: Directory where cookie files will be written.
            filename: Optional target filename.

        Returns:
            bool: True if cookies were saved successfully, otherwise False.
        """
        ...

    @abc.abstractmethod
    def update_cookies(self, cookies: dict[str, str]) -> None:
        """Updates or adds cookie entries.

        Args:
            cookies: A mapping of cookie names to values.
        """
        ...

    @abc.abstractmethod
    def get_cookie(self, key: str) -> str | None:
        """Retrieves a cookie value by name.

        Args:
            key: Cookie name.

        Returns:
            str | None: The cookie value if found, otherwise None.
        """
        ...

    @abc.abstractmethod
    def clear_cookie(self, name: str) -> None:
        """Removes a single cookie.

        Args:
            name: Name of the cookie to remove.
        """
        ...

    @abc.abstractmethod
    def clear_cookies(self) -> None:
        """Removes all stored cookies."""
        ...

    @property
    def headers(self) -> dict[str, str]:
        """Returns a copy of the current session headers.

        Returns:
            dict[str, str]: Header names mapped to their values.
        """
        return self._headers.copy()

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

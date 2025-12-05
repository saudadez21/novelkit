"""
Utility classes for representing HTTP-like responses within the NovelKit
session system.

This module provides lightweight response objects decoupled from any
specific HTTP backend.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterator, Mapping, MutableMapping, Sequence
from typing import Any


class Headers(MutableMapping[str, str]):
    """A case-insensitive, multi-value HTTP header container.

    This class stores header keys in lowercase and supports multiple values
    per header field. Assignment overwrites all values, while `add()` appends
    to the existing list.

    Args:
        headers: Optional initial header mapping or sequence of key-value pairs.
    """

    __slots__ = ("_store",)

    def __init__(
        self,
        headers: Mapping[str, str] | Sequence[tuple[str, str]] | None = None,
    ) -> None:
        self._store: dict[str, list[str]] = defaultdict(list)
        if not headers:
            return

        if isinstance(headers, Mapping):
            for k, v in headers.items():
                self.add(k, v)
        else:
            for k, v in headers:
                self.add(k, v)

    def add(self, key: str, value: str | None) -> None:
        self._store[key.lower()].append(value or "")

    def get_all(self, key: str) -> list[str]:
        return self._store.get(key.lower(), [])

    def __getitem__(self, key: str) -> str:
        vals = self._store.get(key.lower())
        if not vals:
            raise KeyError(key)
        return vals[0]

    def __setitem__(self, key: str, value: str) -> None:
        self._store[key.lower()] = [value]

    def __delitem__(self, key: str) -> None:
        del self._store[key.lower()]

    def __iter__(self) -> Iterator[str]:
        return iter(self._store)

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return key.lower() in self._store

    def __repr__(self) -> str:
        items_preview = ", ".join(f"{k}={len(v)}" for k, v in self._store.items())
        return f"<Headers ({items_preview})>"


class BaseResponse:
    """A lightweight, backend-agnostic HTTP-like response object.

    This response wrapper is used internally by session backends to provide
    consistent access to response content, headers, status codes, and common
    decoding utilities.

    Args:
        content: Raw response body as bytes.
        headers: Optional header mapping or sequence of header pairs.
        status: HTTP-like status code.
        encoding: Default text encoding used when decoding the response body.
    """

    __slots__ = ("content", "headers", "status", "encoding")

    def __init__(
        self,
        *,
        content: bytes,
        headers: Mapping[str, str] | Sequence[tuple[str, str]] | None = None,
        status: int = 200,
        encoding: str = "utf-8",
    ) -> None:
        self.content = content
        self.headers = Headers(headers)
        self.status = status
        self.encoding = encoding

    @property
    def text(self) -> str:
        """Returns the decoded response text.

        The method attempts several common encodings as fallbacks before finally
        decoding with the default encoding using a permissive error handler.
        """
        encodings = [self.encoding, "gb2312", "gb18030", "gbk", "utf-8"]
        for enc in encodings:
            try:
                return self.content.decode(enc)
            except (UnicodeDecodeError, LookupError):
                continue
        return self.content.decode(self.encoding, errors="ignore")

    def json(self) -> Any:
        """Parses the response text as JSON.

        Returns:
            Any: The parsed JSON object.

        Raises:
            json.JSONDecodeError: If the content is not valid JSON.
        """
        return json.loads(self.text)

    @property
    def ok(self) -> bool:
        """Indicates whether the status code represents a successful response.

        Returns:
            bool: True if the status code is less than 400.
        """
        return self.status < 400

    def __repr__(self) -> str:
        return f"<BaseResponse status={self.status} len={len(self.content)}>"

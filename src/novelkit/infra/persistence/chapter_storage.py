"""
Storage module for managing novel chapters in an SQLite database.

This module provides `ChapterStorage`, a lightweight persistence layer used
to store, update, and retrieve chapters. It maintains a small in-memory
cache for refetch flags and exposes a simple CRUD interface over a local
SQLite file.
"""

from __future__ import annotations

__all__ = ["ChapterStorage"]

import contextlib
import json
import sqlite3
import types
from pathlib import Path
from typing import Any, Self

from novelkit.schemas import ChapterDict

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS chapters (
  id           TEXT    NOT NULL PRIMARY KEY,
  title        TEXT    NOT NULL,
  content      TEXT    NOT NULL,
  need_refetch BOOLEAN NOT NULL DEFAULT 0,
  extra        TEXT
);
"""


class ChapterStorage:
    """SQLite-backed storage for novel chapters.

    The storage maintains an internal cache mapping chapter IDs to their
    `need_refetch` flag, allowing the caller to quickly check whether a
    chapter requires refetching without querying SQLite directly.
    """

    def __init__(self, db_path: str | Path) -> None:
        """Initialize storage for a specific book.

        Args:
            db_path: Path to the SQLite file.
        """
        self._db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
        # Cache: chapter id -> need_refetch flag
        self._refetch_flags: dict[str, bool] = {}

    def connect(self) -> None:
        """Open the SQLite connection and initialize schema/cache."""
        if self._conn:
            return

        self._conn = sqlite3.connect(self._db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_CREATE_TABLE_SQL)
        self._conn.commit()
        self._load_existing_keys()

    def exists(self, chap_id: str) -> bool:
        """Check whether a chapter exists in the local store.

        Args:
            chap_id: Chapter identifier.

        Returns:
            True if the chapter is present, else False.
        """
        return chap_id in self._refetch_flags

    def need_refetch(self, chap_id: str) -> bool:
        """Check whether a chapter must be refetched.

        If a chapter ID is unknown, this method conservatively returns True.

        Args:
            chap_id: Chapter identifier.

        Returns:
            True if the chapter requires refetching or is unknown.
        """
        return self._refetch_flags.get(chap_id, True)

    def existing_ids(self) -> set[str]:
        """Return all chapter IDs currently stored.

        Returns:
            A set of chapter IDs.
        """
        return set(self._refetch_flags.keys())

    def clean_ids(self) -> set[str]:
        """Return chapter IDs that do NOT need refetching.

        Returns:
            A set of chapter IDs with `need_refetch=False`.
        """
        return {cid for cid, need in self._refetch_flags.items() if need is False}

    def dirty_ids(self) -> set[str]:
        """Return chapter IDs that DO need refetching.

        Returns:
            A set of chapter IDs with `need_refetch=True`.
        """
        return {cid for cid, need in self._refetch_flags.items() if need is True}

    def upsert_chapter(self, data: ChapterDict, need_refetch: bool = False) -> None:
        """Insert or update a single chapter.

        Args:
            data: A `ChapterDict` with fields `id`, `title`, `content`, `extra`.
            need_refetch: Whether the chapter should be marked for refetch.
        """
        chap_id = data["id"]
        title = data["title"]
        content = data["content"]
        extra_json = json.dumps(data["extra"], ensure_ascii=False)

        self.conn.execute(
            """
            INSERT INTO chapters (id, title, content, need_refetch, extra)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                content=excluded.content,
                need_refetch=excluded.need_refetch,
                extra=excluded.extra
            """,
            (chap_id, title, content, int(need_refetch), extra_json),
        )
        self.conn.commit()
        self._refetch_flags[chap_id] = need_refetch

    def upsert_chapters(
        self, data: list[ChapterDict], need_refetch: bool = False
    ) -> None:
        """Insert or update multiple chapters in one transaction.

        Args:
            data: A list of `ChapterDict` objects.
            need_refetch: Whether all chapters should be marked for refetch.
        """
        if not data:
            return

        records = []
        for chapter in data:
            chap_id = chapter["id"]
            title = chapter["title"]
            content = chapter["content"]
            extra_json = json.dumps(chapter["extra"], ensure_ascii=False)
            records.append((chap_id, title, content, int(need_refetch), extra_json))
            self._refetch_flags[chap_id] = need_refetch

        self.conn.executemany(
            """
            INSERT INTO chapters (id, title, content, need_refetch, extra)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                content=excluded.content,
                need_refetch=excluded.need_refetch,
                extra=excluded.extra
            """,
            records,
        )
        self.conn.commit()

    def get_chapter(self, chap_id: str) -> ChapterDict | None:
        """Retrieve a single chapter by ID.

        Args:
            chap_id: Chapter identifier.

        Returns:
            A `ChapterDict` if found; otherwise None.
        """
        cur = self.conn.execute(
            "SELECT id, title, content, extra FROM chapters WHERE id = ?",
            (chap_id,),
        )
        row = cur.fetchone()
        if not row:
            return None

        return ChapterDict(
            id=row["id"],
            title=row["title"],
            content=row["content"],
            extra=self._load_dict(row["extra"]),
        )

    def get_chapters(self, chap_ids: list[str]) -> dict[str, ChapterDict | None]:
        """Retrieve multiple chapters by ID in a single query.

        Args:
            chap_ids: List of chapter identifiers.

        Returns:
            A dictionary mapping each ID to a `ChapterDict` or None.
        """
        if not chap_ids:
            return {}

        placeholders = ",".join("?" for _ in chap_ids)
        query = f"""
            SELECT id, title, content, extra
              FROM chapters
             WHERE id IN ({placeholders})
        """
        rows = self.conn.execute(query, tuple(chap_ids)).fetchall()

        result: dict[str, ChapterDict | None] = dict.fromkeys(chap_ids)
        for row in rows:
            result[row["id"]] = ChapterDict(
                id=row["id"],
                title=row["title"],
                content=row["content"],
                extra=self._load_dict(row["extra"]),
            )
        return result

    def delete_chapter(self, chap_id: str) -> bool:
        """Delete a single chapter.

        Args:
            chap_id: Chapter identifier.

        Returns:
            True if a chapter was deleted, otherwise False.
        """
        cur = self.conn.execute(
            "DELETE FROM chapters WHERE id = ?",
            (chap_id,),
        )
        self.conn.commit()

        self._refetch_flags.pop(chap_id, None)

        return (cur.rowcount or 0) > 0

    def delete_chapters(self, chap_ids: list[str]) -> int:
        """Delete multiple chapters in a single transaction.

        Args:
            chap_ids: List of chapter identifiers.

        Returns:
            The number of deleted rows.
        """
        if not chap_ids:
            return 0

        unique_ids = set(chap_ids)

        placeholders = ",".join("?" for _ in unique_ids)
        query = f"DELETE FROM chapters WHERE id IN ({placeholders})"
        cur = self.conn.execute(query, tuple(unique_ids))
        self.conn.commit()

        for cid in unique_ids:
            self._refetch_flags.pop(cid, None)

        return cur.rowcount or 0

    def vacuum(self) -> None:
        """Rebuild the SQLite file and reclaim disk space."""
        self.conn.execute("VACUUM")
        self.conn.commit()

    def close(self) -> None:
        """Close the database connection and clear caches."""
        if self._conn is None:
            return

        with contextlib.suppress(Exception):
            self._conn.close()

        self._conn = None
        self._refetch_flags.clear()

    @property
    def conn(self) -> sqlite3.Connection:
        """Return the active SQLite connection.

        Raises:
            RuntimeError: If the connection has not been established.
        """
        if self._conn is None:
            raise RuntimeError(
                "Database connection is not established. Call connect() first."
            )
        return self._conn

    def _load_existing_keys(self) -> None:
        """Populate the in-memory refetch-flag cache from the database."""
        cur = self.conn.execute("SELECT id, need_refetch FROM chapters")
        self._refetch_flags = {
            row["id"]: bool(row["need_refetch"]) for row in cur.fetchall()
        }

    @staticmethod
    def _load_dict(data: str) -> dict[str, Any]:
        """Parse a JSON string.

        Args:
            data: A JSON-encoded string.

        Returns:
            A dictionary parsed from JSON, or an empty dict on error.
        """
        try:
            return json.loads(data) or {}
        except Exception:
            return {}

    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        tb: types.TracebackType | None,
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<ChapterStorage path='{self._db_path}'>"

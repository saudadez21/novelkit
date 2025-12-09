"""
Protocol definitions for user-interface callbacks.

Each UI protocol provides an event sink for feedback and progress reporting.
Concrete implementations may represent CLI, GUI, or web frontends.
"""

from pathlib import Path
from typing import Any, Protocol

from novelkit.schemas import BookConfig, LoginField


class LoginUI(Protocol):
    """Protocol for user interaction during login."""

    async def prompt(
        self,
        fields: list[LoginField],
        prefill: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Prompts the user for login fields.

        Args:
            fields: A list of ``LoginField`` objects describing required inputs.
            prefill: Optional default values for each field.

        Returns:
            A mapping of field identifiers to user-entered values.
        """
        ...

    def on_login_success(self) -> None:
        """Reports that login succeeded."""
        ...

    def on_login_failed(self) -> None:
        """Reports that login credentials were rejected."""
        ...


class DownloadUI(Protocol):
    """Protocol for reporting book download progress."""

    async def on_start(self, book: BookConfig) -> None:
        """Called before a book download begins.

        Args:
            book: The ``BookConfig`` representing the book being downloaded.
        """
        ...

    async def on_progress(self, done: int, total: int) -> None:
        """Reports incremental download progress.

        Args:
            done: Number of completed chapters.
            total: Total number of chapters.
        """
        ...

    async def on_complete(self, book: BookConfig) -> None:
        """Reports that a book download has finished.

        Args:
            book: The completed ``BookConfig``.
        """
        ...


class ExportUI(Protocol):
    """Protocol for reporting export progress and results."""

    def on_start(self, book: BookConfig, fmt: str | None = None) -> None:
        """Called before exporting begins.

        Args:
            book: The book being exported.
            fmt: Optional export format identifier.
        """
        ...

    def on_success(self, book: BookConfig, fmt: str, path: Path) -> None:
        """Reports a successful export.

        Args:
            book: The exported book.
            fmt: Export format, such as ``"epub"`` or ``"txt"``.
            path: The resulting file path.
        """
        ...

    def on_error(self, book: BookConfig, fmt: str | None, error: Exception) -> None:
        """Reports an export failure.

        Args:
            book: The book being exported.
            fmt: Format attempted, or None if unknown.
            error: The exception that occurred.
        """
        ...

    def on_unsupported(self, book: BookConfig, fmt: str) -> None:
        """Reports an attempt to export to an unsupported format.

        Args:
            book: The book being exported.
            fmt: The unsupported format.
        """
        ...


class ProcessUI(Protocol):
    """Protocol for reporting progress during book processing."""

    def on_stage_start(self, book: BookConfig, stage: str) -> None:
        """Called when a processing stage begins.

        Args:
            book: The book undergoing processing.
            stage: The processing stage name.
        """
        ...

    def on_stage_progress(
        self,
        book: BookConfig,
        stage: str,
        done: int,
        total: int,
    ) -> None:
        """Reports progress within a processing stage.

        Args:
            book: The book being processed.
            stage: Name of the active processing stage.
            done: Number of completed items.
            total: Total number of items.
        """
        ...

    def on_stage_complete(self, book: BookConfig, stage: str) -> None:
        """Called when a processing stage completes.

        Args:
            book: The processed book.
            stage: Completed stage name.
        """
        ...

    def on_missing(self, book: BookConfig, what: str, path: Path) -> None:
        """Reports that an expected file or resource is missing.

        Args:
            book: The related book.
            what: Description of the missing item.
            path: Expected path of the missing resource.
        """
        ...

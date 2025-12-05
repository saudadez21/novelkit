"""
State management for user preferences and runtime flags.
"""

__all__ = ["state_mgr"]

import json
from pathlib import Path
from typing import Any

from novelkit.infra.paths import STATE_PATH


class StateManager:
    """Manages persistent state for user preferences and runtime flags.

    This class reads and writes a small JSON file that stores lightweight
    user-specific settings such as preferred language.
    """

    def __init__(self, path: Path = STATE_PATH) -> None:
        """Initialize the state manager.

        Args:
            path: Path to the JSON file used for storing state.
        """
        self._path = path
        self._data = self._load()

    def get_language(self) -> str:
        """Return the user's preferred language.

        Returns:
            str: A language code (defaults to ``"zh_CN"`` if unavailable).
        """
        return self._data.get("lang") or "zh_CN"

    def set_language(self, lang: str) -> None:
        """Set and persist the user's preferred language.

        Args:
            lang: Language code to store (e.g., ``"zh_CN"``, ``"en_US"``).
        """
        self._data["lang"] = lang
        self._save()

    def _load(self) -> dict[str, Any]:
        """Load state data from disk.

        Returns:
            dict[str, Any]: Parsed state data. Returns an empty dict if the
            state file does not exist or contains invalid JSON.
        """
        if not self._path.exists():
            return {}
        try:
            text = self._path.read_text(encoding="utf-8")
            return json.loads(text) or {}
        except Exception:
            return {}

    def _save(self) -> None:
        """Persist current state to disk.

        Ensures the parent directory exists, then writes the JSON file.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(self._data, ensure_ascii=False, indent=2)
        self._path.write_text(content, encoding="utf-8")


state_mgr = StateManager()

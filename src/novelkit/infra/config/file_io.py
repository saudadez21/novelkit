from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from novelkit.infra.paths import DEFAULT_CONFIG_FILE, SETTING_PATH

logger = logging.getLogger(__name__)


def _resolve_file_path(
    user_path: str | Path | None,
    local_filename: list[str],
    fallback_path: Path,
) -> Path | None:
    """
    Resolve the file path to use based on a prioritized lookup order.

    Lookup order:
        1. User-specified path (if provided and exists)
        2. A file in the current working directory matching any of `local_filename`
        3. A globally registered fallback path

    Args:
        user_path: Optional file path explicitly provided by the user.
        local_filename: List of file names to check in the current working directory.
        fallback_path: Fallback path to use if no other match is found.

    Returns:
        A resolved `Path` instance if found, otherwise None.
    """
    if user_path:
        path = Path(user_path).expanduser().resolve()
        if path.is_file():
            return path
        logger.warning("Specified file not found: %s", path)

    for name in local_filename:
        local_path = (Path.cwd() / name).resolve()
        if local_path.is_file():
            logger.debug("Using local file: %s", local_path)
            return local_path

    if fallback_path.is_file():
        return fallback_path.resolve()

    return None


def _load_by_extension(path: Path) -> dict[str, Any]:
    """
    Load a configuration file by its file extension.

    Supports `.json` and `.toml` files. Raises informative errors when parsing
    fails or if the root structure is not a dictionary.

    Args:
        path: Path to the configuration file.

    Returns:
        Parsed configuration data as a dictionary.

    Raises:
        ValueError: If the file extension is unsupported, if parsing fails, or
            if the root element is not a dictionary.
    """
    ext = path.suffix.lower()

    if ext == ".json":
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise ValueError(f"Invalid JSON in {path}: {e}") from e

    elif ext == ".toml":
        try:
            import tomllib

            with path.open("rb") as f:
                data = tomllib.load(f)
        except Exception as e:
            raise ValueError(f"Invalid TOML in {path}: {e}") from e

    else:
        raise ValueError(f"Unsupported config file extension: {ext}")

    if not isinstance(data, dict):
        raise ValueError(f"Config root must be a dict, got {type(data)} in {path}")

    return data


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """
    Load configuration data from a Toml file.

    Resolution order:
        - Explicit `config_path` (if provided)
        - `settings.toml` or `settings.json` in the working directory
        - `SETTING_PATH` fallback path

    Args:
        config_path: Optional explicit configuration file path.

    Returns:
        Parsed configuration as a dictionary.

    Raises:
        FileNotFoundError: If no valid configuration file is found.
        ValueError: If the file cannot be parsed or contains invalid structure.
    """
    path = _resolve_file_path(
        user_path=config_path,
        local_filename=["settings.toml", "settings.json"],
        fallback_path=SETTING_PATH,
    )

    if not path:
        raise FileNotFoundError("No valid config file found.")

    logger.debug("Loading configuration from: %s", path)
    return _load_by_extension(path)


def copy_default_config(target: Path) -> None:
    """
    Copy the bundled default config to the given target path.

    Args:
        target: Destination path for the copied default configuration.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    data = DEFAULT_CONFIG_FILE.read_bytes()
    target.write_bytes(data)


def save_config(
    config: dict[str, Any],
    output_path: str | Path = SETTING_PATH,
) -> None:
    """
    Save configuration data to disk in JSON format.

    Args:
        config: Parsed configuration dictionary.
        output_path: Destination path for the JSON file.

    Raises:
        Exception: If writing to disk fails.
    """
    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        with output.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("Failed to write config JSON '%s': %s", output, e)
        raise

    logger.info("Configuration saved to JSON: %s", output)


def save_config_file(
    source_path: str | Path, output_path: str | Path = SETTING_PATH
) -> None:
    """
    Load a TOML/JSON configuration file and export it as JSON.

    Args:
        source_path: Path to the source TOML/JSON file.
        output_path: Path to the output JSON file.

    Raises:
        FileNotFoundError: If the source file does not exist.
        ValueError: If the source file is invalid or cannot be parsed.
        Exception: If saving the JSON output fails.
    """
    source = Path(source_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Source file not found: {source}")

    data = _load_by_extension(source)
    save_config(data, output_path)

import hashlib
from pathlib import Path
from urllib.parse import unquote, urlparse


class SafeDict(dict[str, str]):
    """Dictionary that returns `{key}` when a missing key is accessed."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def format_filename(
    template: str,
    *,
    append_timestamp: bool = False,
    timestamp_format: str = "%Y%m%d_%H%M%S",
    suffix: str = "",
    **fields: str,
) -> str:
    """Generate a filename from a template and optional keyword fields.

    The template may contain placeholders. Missing fields will remain in
    `{placeholder}` form instead of raising an error.

    Args:
        template: Template string used to build the filename.
        append_timestamp: Whether to append a timestamp to the filename.
        timestamp_format: The `strftime` format for the timestamp.
        suffix: Optional filename suffix (e.g. ".txt").
        **fields: Extra named values injected into the template.

    Returns:
        The formatted filename.
    """
    name = template.format_map(SafeDict(**fields))

    if append_timestamp:
        from datetime import datetime

        name += f"_{datetime.now().strftime(timestamp_format)}"

    return f"{name}{suffix}"


def url_to_hashed_name(
    url: str,
    *,
    name: str | None = None,
    suffix: str = ".bin",
) -> str:
    """Generate a hashed filename from a URL while preserving its extension.

    If the URL has a file extension, it will be used. Otherwise,
    `suffix` is applied.

    Args:
        url: The URL from which to derive the filename.
        name: Optional explicit base name. If not provided, the SHA-1 hash
            of the URL is used.
        suffix: Suffix to use when the URL lacks an extension.

    Returns:
        The generated filename.
    """
    parsed = urlparse(url)
    path = Path(unquote(parsed.path))
    url_suffix = (path.suffix or "").lower()

    if not url_suffix:
        url_suffix = suffix

    name = name or hashlib.sha1(url.encode("utf-8")).hexdigest()
    return f"{name}{url_suffix}"

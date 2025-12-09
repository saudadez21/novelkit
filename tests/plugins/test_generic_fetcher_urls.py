from pathlib import Path

import pytest

from novelkit.plugins.base.fetcher import GenericFetcher
from novelkit.plugins.registry import hub

SITES_DIR = Path(__file__).parents[2] / "src" / "novelkit" / "plugins" / "sites"

# base URL fields to validate
BASE_URL_FIELDS = [
    "BASE_URL",
    "INFO_BASE_URL",
    "CATALOG_BASE_URL",
    "CHAPTER_BASE_URL",
]

# base-url maps to validate
BASE_URL_MAP_FIELDS = [
    "INFO_BASE_URL_MAP",
    "CATALOG_BASE_URL_MAP",
    "CHAPTER_BASE_URL_MAP",
]

# relative URL template fields (must start with "/")
REL_PATH_FIELDS = [
    "BOOK_INFO_PATH",
    "BOOK_CATALOG_PATH",
    "CHAPTER_PATH",
]

# methods for pagination
RELATIVE_METHODS = [
    "relative_info_url",
    "relative_catalog_url",
    "relative_chapter_url",
]


@pytest.mark.parametrize("site_path", [p for p in SITES_DIR.iterdir() if p.is_dir()])
def test_generic_fetcher_url_rules(site_path: Path):
    # skip if site has no fetcher.py
    py_file = site_path / "fetcher.py"
    if not py_file.exists():
        return

    site_key = site_path.name
    fetcher = hub.build_fetcher(site_key)

    cls = fetcher.__class__

    # only validate GenericFetcher subclasses
    if not issubclass(cls, GenericFetcher):
        return

    for field in BASE_URL_FIELDS:
        val = getattr(cls, field, None)
        if val is None:
            continue
        assert not val.endswith("/"), (
            f"{cls.__name__}.{field} must NOT end with '/': {val!r}"
        )

    for field in BASE_URL_MAP_FIELDS:
        url_map = getattr(cls, field, {})
        assert isinstance(url_map, dict), f"{cls.__name__}.{field} must be a dict"
        for key, val in url_map.items():
            assert isinstance(val, str), (
                f"{cls.__name__}.{field}[{key!r}] must be a string"
            )
            assert not val.endswith("/"), (
                f"{cls.__name__}.{field}[{key!r}] must NOT end with '/': {val!r}"
            )

    for field in REL_PATH_FIELDS:
        val = getattr(cls, field, None)
        if not val:
            continue
        assert val.startswith("/"), (
            f"{cls.__name__}.{field} must start with '/': {val!r}"
        )

    for method_name in RELATIVE_METHODS:
        method = getattr(cls, method_name)

        try:
            if method_name == "relative_chapter_url":
                rel = method(book_id="123", chapter_id="456", idx=1)
            else:
                rel = method(book_id="123", idx=1)
        except NotImplementedError:
            continue

        assert isinstance(rel, str), (
            f"{cls.__name__}.{method_name} must return a string"
        )
        assert rel.startswith("/"), (
            f"{cls.__name__}.{method_name} must return a path start with '/': {rel!r}"
        )

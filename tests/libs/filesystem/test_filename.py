import hashlib
import re

from novelkit.libs.filesystem.filename import (
    SafeDict,
    format_filename,
    url_to_hashed_name,
)

# -------------------------------------------------------------
# SafeDict
# -------------------------------------------------------------


def test_safedict_missing_key():
    d = SafeDict(a="1")
    assert d["a"] == "1"
    assert d["missing"] == "{missing}"


# -------------------------------------------------------------
# format_filename
# -------------------------------------------------------------


def test_format_filename_basic():
    result = format_filename("file", append_timestamp=True)
    assert re.match(r"file_\d{8}_\d{6}", result)


def test_format_filename_basic_no_timestamp():
    result = format_filename("file", append_timestamp=False)
    assert result == "file"


def test_format_filename_with_fields_no_timestamp():
    result = format_filename("file_{name}", name="test", append_timestamp=False)
    assert result == "file_test"


def test_format_filename_missing_fields_kept_no_timestamp():
    result = format_filename("file_{missing}", append_timestamp=False)
    assert result == "file_{missing}"


def test_format_filename_with_ext_no_timestamp():
    result = format_filename("file", suffix=".txt", append_timestamp=False)
    assert result == "file.txt"


# -------------------------------------------------------------
# url_to_hashed_name
# -------------------------------------------------------------


def test_url_to_hashed_name_with_existing_suffix():
    url = "https://example.com/path/image.png"
    result = url_to_hashed_name(url)
    assert result.endswith(".png")


def test_url_to_hashed_name_without_suffix():
    url = "https://example.com/path/file"
    result = url_to_hashed_name(url, suffix=".bin")
    assert result.endswith(".bin")


def test_url_to_hashed_name_custom_name():
    url = "https://example.com/path/file"
    result = url_to_hashed_name(url, name="custom", suffix=".dat")
    assert result == "custom.dat"


def test_url_to_hashed_name_name_and_suffix_but_url_has_extension():
    url = "https://example.com/path/file.png"
    result = url_to_hashed_name(url, name="custom", suffix=".dat")
    assert result == "custom.png"


def test_url_to_hashed_name_hash_fallback():
    url = "https://example.com/path/file"
    result = url_to_hashed_name(url)
    hash_value = hashlib.sha1(url.encode("utf-8")).hexdigest()
    assert result.startswith(hash_value)

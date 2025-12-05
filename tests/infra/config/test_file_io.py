import json
from pathlib import Path

import pytest

from novelkit.infra.config.file_io import (
    _load_by_extension,
    copy_default_config,
    load_config,
    save_config,
    save_config_file,
)

# ================================================================
# load_config() and _resolve_file_path behavior tests
# ================================================================


def test_load_config_user_path_exists(tmp_path, monkeypatch):
    """User passed config_path and the file exists -> load it directly."""
    cfgfile = tmp_path / "custom.toml"
    cfgfile.write_text("a = 1\nb = '2'", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    cfg = load_config(config_path=cfgfile)
    assert cfg == {"a": 1, "b": "2"}


def test_load_config_user_path_not_exists(tmp_path):
    """User provided config path but it doesn't exist -> FileNotFoundError."""
    p = tmp_path / "not_exists.toml"
    with pytest.raises(FileNotFoundError):
        load_config(config_path=p)


def test_load_config_local_settings_toml(tmp_path, monkeypatch):
    """No config_path, local settings.toml exists in cwd -> load that file."""
    settings = tmp_path / "settings.toml"
    settings.write_text("a = 1\nb = '2'", encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    cfg = load_config()
    assert cfg == {"a": 1, "b": "2"}


def test_load_config_local_settings_json(tmp_path, monkeypatch):
    """No config_path, local settings.json exists -> load it."""
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"a": 1, "b": "2"}), encoding="utf-8")

    monkeypatch.chdir(tmp_path)

    cfg = load_config()
    assert cfg == {"a": 1, "b": "2"}


def test_load_config_fallback_setting_file(tmp_path, monkeypatch):
    """No config_path, no local file, but SETTING_FILE exists -> load fallback."""
    fallback = tmp_path / "fallback.toml"
    fallback.write_text("a = 1\nb = '2'", encoding="utf-8")

    monkeypatch.setattr(
        "novelkit.infra.config.file_io.SETTING_FILE",
        fallback,
    )
    monkeypatch.chdir(tmp_path)

    cfg = load_config()
    assert cfg == {"a": 1, "b": "2"}


def test_load_config_none_found(tmp_path, monkeypatch):
    """No user path, no local settings, no fallback file -> FileNotFoundError."""
    fake_fallback = tmp_path / "nofile.toml"
    monkeypatch.setattr(
        "novelkit.infra.config.file_io.SETTING_FILE",
        fake_fallback,
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError):
        load_config()


# ================================================================
# _load_by_extension JSON/TOML errors
# ================================================================


def test_load_by_extension_invalid_json(tmp_path):
    """Invalid JSON -> raises ValueError."""
    path = tmp_path / "broken.json"
    path.write_text("{ invalid json", encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        _load_by_extension(path)

    assert "Invalid JSON in" in str(exc.value)


def test_load_by_extension_invalid_toml(tmp_path):
    """Invalid TOML -> raises ValueError."""
    path = tmp_path / "broken.toml"
    path.write_text("a = [1,2,,3]", encoding="utf-8")  # invalid TOML

    with pytest.raises(ValueError) as exc:
        _load_by_extension(path)

    assert "Invalid TOML in" in str(exc.value)


def test_load_by_extension_unsupported_ext(tmp_path):
    """Unsupported extension -> raises ValueError."""
    path = tmp_path / "settings.yaml"
    path.write_text("hello: 1")

    with pytest.raises(ValueError) as exc:
        _load_by_extension(path)

    assert "Unsupported config file extension" in str(exc.value)


def test_load_by_extension_root_not_dict(tmp_path):
    """Parsed root is not dict -> raises ValueError."""
    path = tmp_path / "not_dict.json"
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    with pytest.raises(ValueError) as exc:
        _load_by_extension(path)

    assert "Config root must be a dict" in str(exc.value)


def test_load_by_extension_valid_json(tmp_path):
    """Correct JSON loads properly."""
    path = tmp_path / "ok.json"
    path.write_text(json.dumps({"a": 1, "b": "2"}), encoding="utf-8")

    cfg = _load_by_extension(path)
    assert cfg == {"a": 1, "b": "2"}


def test_load_by_extension_valid_toml(tmp_path):
    """Correct TOML loads properly."""
    path = tmp_path / "ok.toml"
    path.write_text("a = 1\nb = '2'", encoding="utf-8")

    cfg = _load_by_extension(path)
    assert cfg == {"a": 1, "b": "2"}


# ================================================================
# copy_default_config
# ================================================================


def test_copy_default_config(tmp_path, monkeypatch):
    """Monkeypatch DEFAULT_CONFIG_FILE and ensure copy_default_config duplicates it."""
    dummy = tmp_path / "dummy.toml"
    dummy.write_text("a = 1", encoding="utf-8")

    monkeypatch.setattr(
        "novelkit.infra.config.file_io.DEFAULT_CONFIG_FILE",
        dummy,
    )

    target = tmp_path / "out" / "settings.toml"
    copy_default_config(target)

    assert target.read_text(encoding="utf-8") == "a = 1"


# ================================================================
# save_config
# ================================================================


def test_save_config_creates_parent_and_saves(tmp_path):
    outdir = tmp_path / "nested"
    outfile = outdir / "config.json"

    save_config({"a": 1}, outfile)
    assert json.loads(outfile.read_text(encoding="utf-8")) == {"a": 1}


def test_save_config_failure_propagates(tmp_path, monkeypatch):
    outfile = tmp_path / "cannot_write.json"

    # Cause open() to fail intentionally
    def fake_open(*args, **kwargs):
        raise OSError("write fail")

    monkeypatch.setattr(Path, "open", fake_open)

    with pytest.raises(OSError):
        save_config({"a": 1}, outfile)


# ================================================================
# save_config_file
# ================================================================


def test_save_config_file_source_not_found(tmp_path):
    source = tmp_path / "missing.toml"
    with pytest.raises(FileNotFoundError):
        save_config_file(source, tmp_path / "out.json")


def test_save_config_file_valid(tmp_path):
    """Load TOML/JSON -> save JSON."""
    source = tmp_path / "in.toml"
    source.write_text("a = 1\nb = '2'", encoding="utf-8")

    out = tmp_path / "out.json"
    save_config_file(source, out)

    assert json.loads(out.read_text(encoding="utf-8")) == {"a": 1, "b": "2"}


def test_save_config_file_invalid_source(tmp_path):
    """Check that invalid TOML propagates ValueError."""
    source = tmp_path / "bad.toml"
    source.write_text("invalid = [1,,2]")

    with pytest.raises(ValueError):
        save_config_file(source, tmp_path / "out.json")

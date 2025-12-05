from pathlib import Path

import pytest

from novelkit.infra.config.adapter import ConfigAdapter
from novelkit.schemas import (
    BookConfig,
    OCRConfig,
    ProcessorConfig,
)


@pytest.fixture
def sample_config(tmp_path) -> dict:
    """Construct a representative configuration mapping for tests."""
    return {
        "general": {
            "cache_dir": str(tmp_path / "cache"),
            "raw_data_dir": str(tmp_path / "raw"),
            "output_dir": str(tmp_path / "downloads"),
            "request_interval": 1.0,
            "workers": 8,
            "max_connections": 20,
            "max_rps": 500.0,
            "retry_times": 5,
            "backoff_factor": 3.0,
            "timeout": 10.0,
            "storage_batch_size": 2,
            "cache_chapter": False,
            "cache_book_info": False,
            "fetch_inaccessible": True,
            "login_required": False,
            "locale_style": "traditional",
            "backend": "httpx",
            "impersonate": "general-imp",
            "verify_ssl": False,
            "http2": False,
            "proxy": "http://general-proxy",
            "proxy_user": "g-user",
            "proxy_pass": "g-pass",
            "trust_env": True,
            "user_agent": "general-UA",
            "headers": {"X-Header": "general"},
            "parser": {
                "enable_ocr": False,
                "batch_size": 16,
                "remove_watermark": False,
                "model_name": "general-model",
                "input_shape": [3, 32, 320],
                "precision": "fp32",
                "cpu_threads": 4,
                "device": "cpu",
            },
            "export": {
                "render_missing_chapter": False,
                "append_timestamp": False,
                "filename_template": "{title}",
                "include_picture": False,
                "formats": ["epub"],
            },
            "processors": [
                {"name": "normalize", "overwrite": False, "foo": 1},
                {"name": "cleanup", "overwrite": True},
            ],
            "debug": {
                "save_html": True,
                "log_level": "DEBUG",
                "log_dir": str(tmp_path / "logs"),
            },
        },
        "sites": {
            "site1": {
                "request_interval": 2.0,
                "timeout": 5.0,
                "max_rps": 800.0,
                "user_agent": "site-UA",
                "verify_ssl": True,
                "cache_book_info": True,
                "cache_chapter": True,
                # login info
                "username": " user ",
                "password": "",
                "cookies": " cookie=1 ",
                "login_required": True,
                "parser": {
                    "enable_ocr": True,
                    "batch_size": 8,
                    "remove_watermark": True,
                    "use_truncation": False,
                    "model_name": "site-model",
                    "precision": "int8",
                },
                "export": {
                    "render_missing_chapter": True,
                    "append_timestamp": True,
                    "filename_template": "{title}-{author}",
                    "include_picture": True,
                    "split_mode": "volume",
                    "formats": ["epub", "txt"],
                },
                "processors": [
                    {"name": "site-only", "overwrite": False, "bar": 2},
                ],
                "book_ids": [
                    "123",
                    456,
                    {
                        "book_id": "789",
                        "start_id": 1,
                        "end_id": 2,
                        "ignore_ids": [3, 4],
                    },
                ],
            },
            "site2": {
                "book_ids": "123",
            },
            "site3": {
                "book_ids": {
                    "book_id": "123",
                    "start_id": 1,
                    "end_id": 2,
                    "ignore_ids": [3, 4],
                },
            },
            "invalid_1": {
                "book_ids": ["123", ["nested"]],
            },
            "no_site_specific": {},
        },
        "plugins": {
            "enable_local_plugins": True,
            "local_plugins_path": str(tmp_path / "plugins"),
            "override_builtins": True,
        },
    }


# ---------------------------------------------------------------------------
# Basic config retrieval
# ---------------------------------------------------------------------------


def test_get_config(sample_config):
    adapter = ConfigAdapter(sample_config)
    assert adapter.get_config() == sample_config


def test_gen_cfg(sample_config):
    adapter = ConfigAdapter(sample_config)
    assert adapter._gen_cfg() == sample_config["general"]


def test_site_cfg(sample_config):
    adapter = ConfigAdapter(sample_config)
    assert adapter._site_cfg("site1") == sample_config["sites"]["site1"]
    assert adapter._site_cfg("not_exists") == {}


# ---------------------------------------------------------------------------
# FetcherConfig
# ---------------------------------------------------------------------------


def test_get_fetcher_config(sample_config):
    adapter = ConfigAdapter(sample_config)
    cfg = adapter.get_fetcher_config("site1")

    assert cfg.request_interval == 2.0  # site override
    assert cfg.max_rps == 800.0  # site override
    assert cfg.backend == "httpx"  # from general
    assert cfg.locale_style == "traditional"
    assert cfg.session_cfg.timeout == 5.0


# ---------------------------------------------------------------------------
# ParserConfig
# ---------------------------------------------------------------------------


def test_get_parser_config(sample_config):
    adapter = ConfigAdapter(sample_config)
    cfg = adapter.get_parser_config("site1")

    assert cfg.enable_ocr is True
    assert cfg.batch_size == 8
    assert cfg.remove_watermark is True
    assert isinstance(cfg.ocr_cfg, OCRConfig)
    assert cfg.ocr_cfg.precision == "int8"
    assert cfg.ocr_cfg.model_name == "site-model"


def test_dict_to_ocr_cfg_non_dict():
    cfg = ConfigAdapter._dict_to_ocr_cfg("not a dict")  # type: ignore[arg-type]
    assert isinstance(cfg, OCRConfig)


# ---------------------------------------------------------------------------
# ClientConfig
# ---------------------------------------------------------------------------


def test_get_client_config(sample_config):
    adapter = ConfigAdapter(sample_config)
    cfg = adapter.get_client_config("site1")

    # general values
    assert cfg.raw_data_dir.endswith("raw")
    assert cfg.output_dir.endswith("downloads")
    # site override
    assert cfg.request_interval == 2.0
    assert cfg.fetch_inaccessible is True
    assert cfg.cache_book_info is True
    assert cfg.save_html is True  # from general.debug


# ---------------------------------------------------------------------------
# ExporterConfig
# ---------------------------------------------------------------------------


def test_get_exporter_config(sample_config):
    adapter = ConfigAdapter(sample_config)
    cfg = adapter.get_exporter_config("site1")

    assert cfg.render_missing_chapter is True
    assert cfg.append_timestamp is True
    assert cfg.filename_template == "{title}-{author}"
    assert cfg.split_mode == "volume"


# ---------------------------------------------------------------------------
# SessionConfig
# ---------------------------------------------------------------------------


def test_get_session_config(sample_config):
    adapter = ConfigAdapter(sample_config)
    cfg = adapter.get_session_config("site1")

    assert cfg.timeout == 5.0
    assert cfg.verify_ssl is True
    assert cfg.proxy_user == "g-user"  # from general


def test_get_global_session_config(sample_config):
    adapter = ConfigAdapter(sample_config)
    cfg = adapter.get_global_session_config()

    assert cfg.timeout == 10.0
    assert cfg.max_connections == 20


# ---------------------------------------------------------------------------
# Backend, login, formats
# ---------------------------------------------------------------------------


def test_get_global_backend(sample_config):
    adapter = ConfigAdapter(sample_config)
    assert adapter.get_global_backend() == "httpx"


def test_get_login_config(sample_config):
    adapter = ConfigAdapter(sample_config)
    cfg = adapter.get_login_config("site1")

    assert cfg["username"] == "user"
    assert cfg["cookies"] == "cookie=1"
    assert "password" not in cfg  # empty → removed


def test_get_login_required(sample_config):
    adapter = ConfigAdapter(sample_config)
    assert adapter.get_login_required("site1") is True


def test_get_export_fmt(sample_config):
    adapter = ConfigAdapter(sample_config)
    assert adapter.get_export_fmt("site1") == ["epub", "txt"]


# ---------------------------------------------------------------------------
# Plugins
# ---------------------------------------------------------------------------


def test_get_plugins_config(sample_config):
    adapter = ConfigAdapter(sample_config)
    cfg = adapter.get_plugins_config()

    assert cfg["enable_local_plugins"] is True
    assert cfg["override_builtins"] is True
    assert Path(cfg["local_plugins_path"]).name == "plugins"


# ---------------------------------------------------------------------------
# Processors
# ---------------------------------------------------------------------------


def test_get_processor_configs_site_priority(sample_config):
    adapter = ConfigAdapter(sample_config)
    procs = adapter.get_processor_configs("site1")

    assert len(procs) == 1
    assert isinstance(procs[0], ProcessorConfig)
    assert procs[0].name == "site-only"


def test_get_processor_configs_fallback(sample_config):
    adapter = ConfigAdapter(sample_config)
    procs = adapter.get_processor_configs("no_site_specific")

    assert len(procs) == 2
    assert procs[0].name == "normalize"
    assert procs[1].name == "cleanup"


def test_to_processor_cfgs_non_list():
    result = ConfigAdapter._to_processor_cfgs("not a list")  # type: ignore[arg-type]
    assert result == []


def test_to_processor_cfgs_skip_non_dict():
    data = [
        "invalid",
        123,
        ["nested"],
        {"name": "ok", "overwrite": True, "foo": 1},
    ]

    result = ConfigAdapter._to_processor_cfgs(data)

    assert len(result) == 1
    assert result[0].name == "ok"
    assert result[0].overwrite is True
    assert result[0].options == {"foo": 1}


def test_to_processor_cfgs_skip_missing_or_empty_name():
    data = [
        {"overwrite": True},  # no name
        {"name": ""},  # empty name
        {"name": "   "},  # whitespace only
        {"name": "valid", "bar": 2},  # valid
    ]

    result = ConfigAdapter._to_processor_cfgs(data)

    assert len(result) == 1
    assert result[0].name == "valid"
    assert result[0].options == {"bar": 2}


def test_to_processor_cfgs_normal():
    data = [
        {"name": "normalize", "overwrite": False, "foo": 1},
        {"name": "cleanup", "overwrite": True},
    ]

    result = ConfigAdapter._to_processor_cfgs(data)

    assert len(result) == 2

    assert result[0].name == "normalize"
    assert result[0].overwrite is False
    assert result[0].options == {"foo": 1}

    assert result[1].name == "cleanup"
    assert result[1].overwrite is True
    assert result[1].options == {}


# ---------------------------------------------------------------------------
# Book IDs
# ---------------------------------------------------------------------------


def test_get_book_ids_list(sample_config):
    adapter = ConfigAdapter(sample_config)
    ids = adapter.get_book_ids("site1")

    assert len(ids) == 3
    assert isinstance(ids[0], BookConfig)
    assert ids[0].book_id == "123"
    assert ids[1].book_id == "456"
    assert ids[2].start_id == "1"
    assert ids[2].ignore_ids == frozenset({"3", "4"})


def test_get_book_ids_scalar(sample_config):
    adapter = ConfigAdapter(sample_config)
    ids = adapter.get_book_ids("site2")

    assert len(ids) == 1
    assert ids[0].book_id == "123"


def test_get_book_ids_dict(sample_config):
    adapter = ConfigAdapter(sample_config)
    ids = adapter.get_book_ids("site3")

    assert len(ids) == 1
    assert ids[0].start_id == "1"
    assert ids[0].ignore_ids == frozenset({"3", "4"})


def test_get_book_ids_invalid_type(sample_config):
    adapter = ConfigAdapter(sample_config)

    # inject invalid type
    adapter._config["sites"]["site1"]["book_ids"] = 3.14

    with pytest.raises(ValueError):
        adapter.get_book_ids("site1")


def test_dict_to_book_cfg_missing_field():
    with pytest.raises(ValueError):
        ConfigAdapter._dict_to_book_cfg({})


def test_get_book_ids_invalid_item_type(sample_config):
    adapter = ConfigAdapter(sample_config)
    with pytest.raises(ValueError):
        adapter.get_book_ids("invalid_1")


# ---------------------------------------------------------------------------
# Paths: log_dir, cache_dir, raw_data_dir, output_dir
# ---------------------------------------------------------------------------


def test_get_log_level(sample_config):
    adapter = ConfigAdapter(sample_config)
    assert adapter.get_log_level() == "DEBUG"


def test_get_log_dir(sample_config):
    adapter = ConfigAdapter(sample_config)
    p = adapter.get_log_dir()
    assert p.name == "logs"


def test_get_cache_dir(sample_config):
    adapter = ConfigAdapter(sample_config)
    assert adapter.get_cache_dir().name == "cache"


def test_get_raw_data_dir(sample_config):
    adapter = ConfigAdapter(sample_config)
    assert adapter.get_raw_data_dir().name == "raw"


def test_get_output_dir(sample_config):
    adapter = ConfigAdapter(sample_config)
    assert adapter.get_output_dir().name == "downloads"

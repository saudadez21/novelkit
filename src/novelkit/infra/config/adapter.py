from __future__ import annotations

from pathlib import Path
from typing import Any

from novelkit.schemas import (
    BookConfig,
    ClientConfig,
    ExporterConfig,
    FetcherConfig,
    OCRConfig,
    ParserConfig,
    ProcessorConfig,
    SessionConfig,
)


class ConfigAdapter:
    """High-level accessor for general and site-specific configuration.

    All configuration resolution follows the order:

    **general -> site-specific -> built-in defaults**

    Args:
        config (dict[str, Any]): Fully loaded configuration mapping containing
            a ``general`` block and optionally a ``sites`` block.

    Attributes:
        _config (dict[str, Any]): Internal stored configuration mapping.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._config: dict[str, Any] = dict(config)

    def get_config(self) -> dict[str, Any]:
        """Return the full raw configuration mapping.

        Returns:
            dict[str, Any]: The stored configuration.
        """
        return self._config

    def get_fetcher_config(self, site: str) -> FetcherConfig:
        """Build a FetcherConfig by merging general and site overrides.

        Args:
            site (str): Target site key.

        Returns:
            FetcherConfig: Resolved fetcher configuration.
        """
        site_cfg, general_cfg = self._site_cfg(site), self._gen_cfg()
        cfg = {**general_cfg, **site_cfg}

        return FetcherConfig(
            request_interval=cfg.get("request_interval", 0.5),
            max_rps=cfg.get("max_rps", 1000.0),
            backend=cfg.get("backend", "aiohttp"),
            locale_style=cfg.get("locale_style", "simplified"),
            session_cfg=self.get_session_config(site),
        )

    def get_parser_config(self, site: str) -> ParserConfig:
        """Build a ParserConfig by merging general and site overrides.

        Args:
            site (str): Target site key.

        Returns:
            ParserConfig: Resolved parser configuration.
        """
        site_cfg, general_cfg = self._site_cfg(site), self._gen_cfg()
        general_parser = general_cfg.get("parser") or {}
        site_parser = site_cfg.get("parser") or {}
        parser_cfg: dict[str, Any] = {**general_parser, **site_parser}

        return ParserConfig(
            cache_dir=general_cfg.get("cache_dir", "./novel_cache"),
            use_truncation=bool(parser_cfg.get("use_truncation", True)),
            enable_ocr=bool(parser_cfg.get("enable_ocr", False)),
            batch_size=int(parser_cfg.get("batch_size", 32)),
            remove_watermark=bool(parser_cfg.get("remove_watermark", False)),
            ocr_cfg=self._dict_to_ocr_cfg(parser_cfg),
        )

    def get_client_config(self, site: str) -> ClientConfig:
        """Build a ClientConfig by merging general and site overrides.

        Args:
            site (str): Target site key.

        Returns:
            ClientConfig: Resolved client configuration.
        """
        site_cfg, general_cfg = self._site_cfg(site), self._gen_cfg()
        cfg = {**general_cfg, **site_cfg}
        debug_cfg = general_cfg.get("debug") or {}

        return ClientConfig(
            raw_data_dir=general_cfg.get("raw_data_dir", "./raw_data"),
            cache_dir=general_cfg.get("cache_dir", "./novel_cache"),
            output_dir=general_cfg.get("output_dir", "./downloads"),
            request_interval=cfg.get("request_interval", 0.5),
            retry_times=cfg.get("retry_times", 3),
            backoff_factor=cfg.get("backoff_factor", 2.0),
            workers=cfg.get("workers", 4),
            storage_batch_size=cfg.get("storage_batch_size", 1),
            cache_book_info=bool(cfg.get("cache_book_info", True)),
            cache_chapter=cfg.get("cache_chapter", True),
            fetch_inaccessible=cfg.get("fetch_inaccessible", False),
            save_html=bool(debug_cfg.get("save_html", False)),
            fetcher_cfg=self.get_fetcher_config(site),
            parser_cfg=self.get_parser_config(site),
        )

    def get_exporter_config(self, site: str) -> ExporterConfig:
        """Build an ExporterConfig by merging general and site overrides.

        Args:
            site (str): Target site key.

        Returns:
            ExporterConfig: Resolved exporter settings.
        """
        site_cfg, general_cfg = self._site_cfg(site), self._gen_cfg()
        general_export = general_cfg.get("export") or {}
        site_export = site_cfg.get("export") or {}
        out = {**general_export, **site_export}

        return ExporterConfig(
            render_missing_chapter=out.get("render_missing_chapter", True),
            append_timestamp=out.get("append_timestamp", True),
            filename_template=out.get("filename_template", "{title}_{author}"),
            include_picture=out.get("include_picture", True),
            split_mode=out.get("split_mode", "book"),
        )

    def get_session_config(self, site: str) -> SessionConfig:
        """Build a SessionConfig by merging general and site overrides.

        Args:
            site (str): Target site key.

        Returns:
            SessionConfig: Resolved session configuration.
        """
        site_cfg, general_cfg = self._site_cfg(site), self._gen_cfg()
        cfg = {**general_cfg, **site_cfg}

        return SessionConfig(
            timeout=cfg.get("timeout", 10.0),
            max_connections=cfg.get("max_connections", 10),
            user_agent=cfg.get("user_agent"),
            headers=cfg.get("headers"),
            impersonate=cfg.get("impersonate"),
            verify_ssl=cfg.get("verify_ssl", True),
            http2=cfg.get("http2", True),
            trust_env=cfg.get("trust_env", False),
            proxy=cfg.get("proxy"),
            proxy_user=cfg.get("proxy_user"),
            proxy_pass=cfg.get("proxy_pass"),
        )

    def get_global_session_config(self) -> SessionConfig:
        """Return a SessionConfig based solely on general settings.

        Returns:
            SessionConfig: Session configuration without site overrides.
        """
        general_cfg = self._gen_cfg()

        return SessionConfig(
            timeout=general_cfg.get("timeout", 10.0),
            max_connections=general_cfg.get("max_connections", 10),
            user_agent=general_cfg.get("user_agent"),
            headers=general_cfg.get("headers"),
            impersonate=general_cfg.get("impersonate"),
            verify_ssl=general_cfg.get("verify_ssl", True),
            http2=general_cfg.get("http2", True),
            trust_env=general_cfg.get("trust_env", False),
            proxy=general_cfg.get("proxy"),
            proxy_user=general_cfg.get("proxy_user"),
            proxy_pass=general_cfg.get("proxy_pass"),
        )

    def get_global_backend(self) -> str:
        """Return the backend string from general configuration.

        Returns:
            str: Backend name or ``"aiohttp"`` if unspecified.
        """
        general_cfg = self._gen_cfg()
        backend = general_cfg.get("backend")
        return backend if isinstance(backend, str) else "aiohttp"

    def get_login_config(self, site: str) -> dict[str, str]:
        """Extract login-related fields for the given site.

        Args:
            site (str): Target site key.

        Returns:
            dict[str, str]: Non-empty {username, password, cookies}.
        """
        site_cfg = self._site_cfg(site)
        out: dict[str, str] = {}
        for key in ("username", "password", "cookies"):
            val = site_cfg.get(key, "")
            if isinstance(val, str):
                s = val.strip()
                if s:
                    out[key] = s
        return out

    def get_login_required(self, site: str) -> bool:
        """Return whether login is required for this site.

        Args:
            site (str): Target site key.

        Returns:
            bool: True if login is required.
        """
        site_cfg, general_cfg = self._site_cfg(site), self._gen_cfg()
        cfg = {**general_cfg, **site_cfg}
        return bool(cfg.get("login_required", False))

    def get_export_fmt(self, site: str) -> list[str]:
        """Return enabled export formats for the given site.

        Args:
            site (str): Target site key.

        Returns:
            list[str]: Export format names or empty list.
        """
        site_cfg, general_cfg = self._site_cfg(site), self._gen_cfg()
        general_exportt = general_cfg.get("export") or {}
        site_export = site_cfg.get("export") or {}
        out = {**general_exportt, **site_export}
        fmt = out.get("formats")
        return fmt if isinstance(fmt, list) else []

    def get_plugins_config(self) -> dict[str, Any]:
        """Return normalized plugin-related configuration.

        Returns:
            dict[str, Any]: Plugin configuration mapping.
        """
        plugins_cfg = self._config.get("plugins") or {}
        return {
            "enable_local_plugins": plugins_cfg.get("enable_local_plugins", False),
            "local_plugins_path": plugins_cfg.get("local_plugins_path") or "",
            "override_builtins": plugins_cfg.get("override_builtins", False),
        }

    def get_processor_configs(self, site: str) -> list[ProcessorConfig]:
        """Return ProcessorConfig list for the given site.

        Site-specific processors override general processors entirely.

        Args:
            site (str): Target site key.

        Returns:
            list[ProcessorConfig]: Processor configuration list.
        """
        site_cfg, general_cfg = self._site_cfg(site), self._gen_cfg()

        site_rows = site_cfg.get("processors") or []
        site_procs = self._to_processor_cfgs(site_rows)
        general_rows = general_cfg.get("processors") or []
        general_procs = self._to_processor_cfgs(general_rows)

        return site_procs if site_procs else general_procs

    def get_book_ids(self, site: str) -> list[BookConfig]:
        """Normalize and return BookConfig list for the given site.

        Args:
            site (str): Target site key.

        Returns:
            list[BookConfig]: Normalized target books.

        Raises:
            ValueError: If ``book_ids`` or any element has invalid type.
        """
        raw = self._site_cfg(site).get("book_ids", [])

        # Normalize to list
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, (str, int, dict)):
            items = [raw]
        else:
            raise ValueError(
                f"book_ids must be str|int|dict|list, got {type(raw).__name__}"
            )

        result: list[BookConfig] = []
        for item in items:
            if isinstance(item, (str, int)):
                result.append(self._dict_to_book_cfg({"book_id": item}))
            elif isinstance(item, dict):
                result.append(self._dict_to_book_cfg(item))
            else:
                raise ValueError(
                    f"Invalid book entry: expected str|int|dict, got {type(item).__name__}"
                )
        return result

    def get_log_level(self) -> str:
        """Return the configured logging level.

        Returns:
            str: Logging level or ``"INFO"`` if missing.
        """
        debug_cfg = self._gen_cfg().get("debug", {})
        return debug_cfg.get("log_level") or "INFO"

    def get_log_dir(self) -> Path:
        """Return directory for log files.

        Returns:
            Path: Absolute log directory path.
        """
        debug_cfg = self._gen_cfg().get("debug", {})
        log_dir = debug_cfg.get("log_dir") or "./logs"
        return Path(log_dir).expanduser().resolve()

    def get_cache_dir(self) -> Path:
        """Return directory for cache storage.

        Returns:
            Path: Absolute cache directory path.
        """
        cache_dir = self._gen_cfg().get("cache_dir") or "./novel_cache"
        return Path(cache_dir).expanduser().resolve()

    def get_raw_data_dir(self) -> Path:
        """Return directory used for raw scraped data.

        Returns:
            Path: Absolute raw data storage path.
        """
        raw_data_dir = self._gen_cfg().get("raw_data_dir") or "./raw_data"
        return Path(raw_data_dir).expanduser().resolve()

    def get_output_dir(self) -> Path:
        """Return directory for final output files.

        Returns:
            Path: Absolute output directory path.
        """
        output_dir = self._gen_cfg().get("output_dir") or "./downloads"
        return Path(output_dir).expanduser().resolve()

    def _gen_cfg(self) -> dict[str, Any]:
        """Return general configuration mapping.

        Returns:
            dict[str, Any]: ``general`` config or empty dict.
        """
        general = self._config.get("general")
        return general if isinstance(general, dict) else {}

    def _site_cfg(self, site: str) -> dict[str, Any]:
        """Return configuration block for the given site.

        Args:
            site (str): Site name.

        Returns:
            dict[str, Any]: Site configuration or empty dict.
        """
        sites_cfg = self._config.get("sites") or {}
        value = sites_cfg.get(site)
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _dict_to_book_cfg(data: dict[str, Any]) -> BookConfig:
        """Convert raw dict into BookConfig.

        Args:
            data (dict[str, Any]): Mapping containing at least ``book_id``.

        Returns:
            BookConfig: Normalized book configuration.

        Raises:
            ValueError: If ``book_id`` is missing.
        """
        if "book_id" not in data:
            raise ValueError("Missing required field 'book_id'")

        book_id = str(data["book_id"])
        start_id = str(data["start_id"]) if "start_id" in data else None
        end_id = str(data["end_id"]) if "end_id" in data else None

        ignore_ids: frozenset[str] = frozenset()
        if "ignore_ids" in data:
            ignore_ids = frozenset(str(x) for x in data["ignore_ids"])

        return BookConfig(
            book_id=book_id,
            start_id=start_id,
            end_id=end_id,
            ignore_ids=ignore_ids,
        )

    @staticmethod
    def _dict_to_ocr_cfg(data: dict[str, Any]) -> OCRConfig:
        """Convert raw mapping to OCRConfig.

        Non-dict values return a default OCRConfig.

        Args:
            data (dict[str, Any]): OCR configuration mapping.

        Returns:
            OCRConfig: OCR settings object.
        """
        if not isinstance(data, dict):
            return OCRConfig()

        ishape = data.get("input_shape")
        if isinstance(ishape, list):
            # [C, H, W] -> (C, H, W)
            ishape = tuple(ishape)

        return OCRConfig(
            model_name=data.get("model_name"),
            model_dir=data.get("model_dir"),
            input_shape=ishape,
            device=data.get("device"),
            precision=data.get("precision", "fp32"),
            cpu_threads=data.get("cpu_threads", 10),
            enable_hpi=data.get("enable_hpi", False),
        )

    @staticmethod
    def _to_processor_cfgs(data: list[dict[str, Any]]) -> list[ProcessorConfig]:
        """Convert raw processor rows into ProcessorConfig objects.

        Args:
            data (list[dict[str, Any]]): Raw processor configuration rows.

        Returns:
            list[ProcessorConfig]: Parsed processor definitions.
        """
        if not isinstance(data, list):
            return []

        result: list[ProcessorConfig] = []
        for row in data:
            if not isinstance(row, dict):
                continue

            name = str(row.get("name", "")).strip().lower()
            if not name:
                continue

            overwrite = bool(row.get("overwrite", False))
            # Pass everything else as options.
            opts = {k: v for k, v in row.items() if k not in ("name", "overwrite")}
            result.append(ProcessorConfig(name=name, overwrite=overwrite, options=opts))

        return result

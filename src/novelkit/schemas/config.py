"""
Defines structured configuration models using dataclasses.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OCRConfig:
    model_name: str | None = None
    model_dir: str | None = None
    input_shape: tuple[int, int, int] | None = None
    device: str | None = None
    precision: str = "fp32"
    cpu_threads: int = 10
    enable_hpi: bool = False


@dataclass
class SessionConfig:
    timeout: float = 10.0
    max_connections: int = 10
    user_agent: str | None = None
    headers: dict[str, str] | None = None
    cookies: dict[str, str] | None = None
    impersonate: str | None = None
    verify_ssl: bool = True
    http2: bool = True
    trust_env: bool = False
    proxy: str | None = None
    proxy_user: str | None = None
    proxy_pass: str | None = None


@dataclass
class ExporterConfig:
    render_missing_chapter: bool = True
    append_timestamp: bool = True
    filename_template: str = "{title}_{author}"
    include_picture: bool = True
    split_mode: str = "book"


@dataclass
class ParserConfig:
    cache_dir: str = "./novel_cache"
    use_truncation: bool = True
    enable_ocr: bool = False
    batch_size: int = 32
    remove_watermark: bool = False
    ocr_cfg: OCRConfig = field(default_factory=OCRConfig)


@dataclass
class FetcherConfig:
    request_interval: float = 0.5
    max_rps: float = 1000.0
    backend: str = "aiohttp"
    locale_style: str = "simplified"
    session_cfg: SessionConfig = field(default_factory=SessionConfig)


@dataclass
class ClientConfig:
    cache_dir: str = "./novel_cache"
    raw_data_dir: str = "./raw_data"
    output_dir: str = "./downloads"
    request_interval: float = 0.5
    retry_times: int = 3
    backoff_factor: float = 2.0
    workers: int = 4
    storage_batch_size: int = 1
    cache_book_info: bool = True
    cache_chapter: bool = True
    fetch_inaccessible: bool = False
    save_html: bool = False
    fetcher_cfg: FetcherConfig = field(default_factory=FetcherConfig)
    parser_cfg: ParserConfig = field(default_factory=ParserConfig)


@dataclass
class ProcessorConfig:
    name: str  # "cleaner" | "corrector" | ...
    overwrite: bool = False
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BookConfig:
    book_id: str
    start_id: str | None = None
    end_id: str | None = None
    ignore_ids: frozenset[str] = field(default_factory=frozenset)

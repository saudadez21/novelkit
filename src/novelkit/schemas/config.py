"""
Defines structured configuration models using dataclasses.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OCRConfig:
    """Configuration for PaddleOCR processing.

    Attributes:
        model_name: Optional name of the OCR model to use.
        model_dir: Directory containing model files.
        input_shape: Expected input shape for the OCR model.
        device: Execution device such as "cpu" or "cuda".
        precision: Model precision ("fp32", "fp16", etc.).
        cpu_threads: Number of CPU threads to allocate.
        enable_hpi: Whether to use hardware performance improvements.
    """

    model_name: str | None = None
    model_dir: str | None = None
    input_shape: tuple[int, int, int] | None = None
    device: str | None = None
    precision: str = "fp32"
    cpu_threads: int = 10
    enable_hpi: bool = False


@dataclass
class SessionConfig:
    """Configuration for HTTP session behavior.

    Attributes:
        timeout: Request timeout in seconds.
        max_connections: Maximum number of concurrent connections.
        user_agent: Custom User-Agent string.
        headers: Additional headers to attach to requests.
        cookies: Default cookies for the session.
        impersonate: Browser impersonation mode. (`curl_cffi`)
        verify_ssl: Whether to verify SSL certificates.
        http2: Whether HTTP/2 should be used. (`httpx`)
        trust_env: Whether environment variables are used for proxies.
        proxy: Proxy server URL.
        proxy_user: Proxy authentication username.
        proxy_pass: Proxy authentication password.
    """

    timeout: float = 10.0
    max_connections: int = 10
    user_agent: str | None = None
    headers: dict[str, str] | None = None
    cookies: dict[str, str] | None = None
    impersonate: str | None = "chrome"
    verify_ssl: bool = True
    http2: bool = True
    trust_env: bool = False
    proxy: str | None = None
    proxy_user: str | None = None
    proxy_pass: str | None = None


@dataclass
class ExporterConfig:
    """Configuration for exporting processed novel output.

    Attributes:
        render_missing_chapter: Whether to include placeholders for missing chapters.
        append_timestamp: Whether to append timestamps to exported filenames.
        filename_template: Template string for output filenames.
        include_picture: Whether to include images in the export.
        split_mode: Strategy for splitting export files.
    """

    render_missing_chapter: bool = True
    append_timestamp: bool = True
    filename_template: str = "{title}_{author}"
    include_picture: bool = True
    split_mode: str = "book"


@dataclass
class ParserConfig:
    """Configuration for parsing downloaded novel content.

    Attributes:
        cache_dir: Directory to store parser cache.
        use_truncation: Whether long texts should be truncated.
        enable_ocr: Whether OCR-based processing is enabled.
        batch_size: OCR batch size.
        remove_watermark: Whether to attempt removing watermarks from image-based
            chapters on supported sites.
        ocr_cfg: OCR configuration used when enable_ocr is True.
    """

    cache_dir: str = "./novel_cache"
    use_truncation: bool = True
    enable_ocr: bool = False
    batch_size: int = 32
    remove_watermark: bool = False
    ocr_cfg: OCRConfig = field(default_factory=OCRConfig)


@dataclass
class FetcherConfig:
    """Configuration for fetching novel content from remote sources.

    Attributes:
        request_interval: Delay between requests to avoid rate limits.
        max_rps: Maximum allowed requests per second.
        backend: HTTP backend name (aiohttp, httpx, curl_cffi).
        locale_style: Locale preferences for text normalization.
        session_cfg: HTTP session configuration.
    """

    request_interval: float = 0.5
    max_rps: float = 1000.0
    backend: str = "aiohttp"
    locale_style: str = "simplified"
    session_cfg: SessionConfig = field(default_factory=SessionConfig)


@dataclass
class ClientConfig:
    """Top-level configuration for the NovelKit client.

    Attributes:
        cache_dir: Directory for cache data.
        raw_data_dir: Directory for raw downloaded content.
        output_dir: Directory for exported output files.
        request_interval: Request interval override.
        retry_times: Number of retry attempts on failure.
        backoff_factor: Retry backoff multiplier.
        workers: Number of concurrent workers.
        storage_batch_size: Items stored per batch.
        cache_book_info: Whether metadata is cached.
        cache_chapter: Whether chapter content is cached.
        fetch_inaccessible: Whether to try fetching restricted chapters.
        save_html: Whether to save original HTML snapshots (debug).
        fetcher_cfg: Configuration for the fetcher.
        parser_cfg: Configuration for the parser.
    """

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
    """Configuration for a text processor step.

    Attributes:
        name: Processor identifier (e.g., "cleaner", "zh_convert").
        overwrite: Whether the processor overwrites existing output.
        options: Additional processor-specific options.
    """

    name: str  # "cleaner" | "zh_convert" | ...
    overwrite: bool = False
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BookConfig:
    """Configuration describing a specific book to fetch.

    Attributes:
        book_id: Unique identifier for the book.
        start_id: Optional starting chapter ID.
        end_id: Optional ending chapter ID.
        ignore_ids: Set of chapter IDs that should be skipped.
    """

    book_id: str
    start_id: str | None = None
    end_id: str | None = None
    ignore_ids: frozenset[str] = field(default_factory=frozenset)

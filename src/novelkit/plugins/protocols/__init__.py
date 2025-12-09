"""
Protocol exports for plugin components.

This module aggregates all protocol interfaces used by the plugin ecosystem,
including client, fetcher, parser, processor, and UI callback definitions.
"""

__all__ = [
    "ClientProtocol",
    "_ClientContext",
    "FetcherProtocol",
    "ParserProtocol",
    "ProcessorProtocol",
    "DownloadUI",
    "ExportUI",
    "LoginUI",
    "ProcessUI",
]

from .client import ClientProtocol, _ClientContext
from .fetcher import FetcherProtocol
from .parser import ParserProtocol
from .processor import ProcessorProtocol
from .ui import DownloadUI, ExportUI, LoginUI, ProcessUI

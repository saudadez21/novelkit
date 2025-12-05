"""
Unified interface for loading and adapting configuration files.
"""

__all__ = [
    "copy_default_config",
    "load_config",
    "save_config_file",
    "ConfigAdapter",
]

from .adapter import ConfigAdapter
from .file_io import (
    copy_default_config,
    load_config,
    save_config_file,
)

from importlib.resources import files

from platformdirs import user_config_path

PACKAGE_NAME = "novelkit"  # Python package name

# -----------------------------------------------------------------------------
# User-writable directories & files
# -----------------------------------------------------------------------------

# Base config directory (e.g. ~/AppData/Local/novel_downloader/)
USER_CONFIG_DIR = user_config_path(PACKAGE_NAME, appauthor=False)

STATE_PATH = USER_CONFIG_DIR / "state.json"
SETTING_PATH = USER_CONFIG_DIR / "settings.json"

# -----------------------------------------------------------------------------
# Embedded resources
# -----------------------------------------------------------------------------

RES = files("novelkit.resources")

# Config
DEFAULT_CONFIG_FILE = RES.joinpath("config", "settings.sample.toml")

# Default config filename (used when copying embedded template)
DEFAULT_CONFIG_FILENAME = "settings.toml"

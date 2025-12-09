# User-Interface Protocols

NovelKit defines several optional UI interfaces used to report progress,
prompt for credentials, and surface errors.

These UI objects are provided by the caller (CLI, TUI, GUI, web frontend, etc.)
and allow higher-level feedback without coupling to any UI framework.

All UI protocols are defined in:

```
novelkit.plugins.protocols.ui
```

The sections below describe how they are used and how to implement them.

---

::: novelkit.plugins.protocols.ui.LoginUI

### Example: simple CLI login UI

```py
from novelkit.plugins.protocols.ui import LoginUI

class SimpleLoginUI:
    async def prompt(self, fields, prefill=None):
        result = {}
        for field in fields:
            key = field.key
            label = field.label or key
            default = (prefill or {}).get(key, "")
            prompt = f"{label} [{default}]: "
            value = input(prompt).strip() or default
            result[key] = value
        return result

    def on_login_success(self):
        print("Login successful!")

    def on_login_failed(self):
        print("Login failed. Please try again.")
```

---

::: novelkit.plugins.protocols.ui.DownloadUI

### Example: CLI progress bar

```py
class SimpleDownloadUI:
    async def on_start(self, book):
        print(f"Downloading: {book.book_id}")

    async def on_progress(self, done, total):
        print(f"Progress: {done}/{total}", end="\r")

    async def on_complete(self, book):
        print(f"\nDownload complete: {book.book_id}")
```

---

::: novelkit.plugins.protocols.ui.ExportUI

### Example

```py
class SimpleExportUI:
    def on_start(self, book, fmt=None):
        print(f"Exporting {fmt or ''} for {book.book_id}...")

    def on_success(self, book, fmt, path):
        print(f"[OK] {fmt} exported → {path}")

    def on_error(self, book, fmt, error):
        print(f"[ERROR] {fmt}: {error}")

    def on_unsupported(self, book, fmt):
        print(f"[SKIP] Format not supported: {fmt}")
```

---

::: novelkit.plugins.protocols.ui.ProcessUI

### Example

```py
class SimpleProcessUI:
    def on_stage_start(self, book, stage):
        print(f"Processing stage: {stage}")

    def on_stage_progress(self, book, stage, done, total):
        print(f"{stage}: {done}/{total}", end="\r")

    def on_stage_complete(self, book, stage):
        print(f"{stage} complete")

    def on_missing(self, book, what, path):
        print(f"[WARN] Missing {what}: {path}")
```

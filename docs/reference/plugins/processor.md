# Processor

A **Processor** transforms already-parsed, structured data into a cleaner,
normalized, or enriched form.

Typical use cases include:

- removing watermarks or ad lines
- converting punctuation or character sets
- trimming whitespace
- rewriting titles
- inserting user-defined annotations
- restructuring chapters or metadata

Processors are fully optional, and multiple processor stages may be chained.

---

## Processor Key Rules

A processor's registration key is derived from its module path.

When the processor lives directly under `processors/`, the key is simply:

```
<filename without .py>
```

Example:

```
novel_plugins/processors/cleanup.py
```

key:

```
cleanup
```

If the processor is inside **subpackages**, the key becomes the full dotted path
(relative to the `processors` package):

Example:

```
novel_plugins/processors/text/zh_convert.py
```

key:

```
text.zh_convert
```

This allows grouping processors by category while still registering them uniquely.

---

::: novelkit.plugins.protocols.processor.ProcessorProtocol

---

## Example: Implementing a Simple Processor

Below is a minimal processor that normalizes whitespace, removes known
advertisement fragments, and trims chapter titles.

```py
from __future__ import annotations
from typing import Any

from novelkit.plugins.registry import hub
from novelkit.schemas import BookInfoDict, ChapterDict

@hub.register_processor()
class SimpleCleanupProcessor:
    """Example processor that cleans metadata and chapter text."""

    # ads or boilerplate phrases to remove from chapter content
    AD_PATTERNS = {
        "请收藏本站",
        "手机阅读更方便",
        "最新章节",
    }

    def __init__(self, config: dict[str, Any] | None = None, **kwargs: Any) -> None:
        self.config = config or {}

    def process_book_info(self, book_info: BookInfoDict) -> BookInfoDict:
        # Normalize book title and author fields
        book_info["book_name"] = book_info["book_name"].strip()
        book_info["author"] = book_info["author"].strip()
        return book_info

    def process_chapter(self, chapter: ChapterDict) -> ChapterDict:
        # Clean title
        chapter["title"] = chapter["title"].strip()

        # Remove ad lines
        cleaned_lines = []
        for ln in chapter["content"].splitlines():
            if not any(pat in ln for pat in self.AD_PATTERNS):
                cleaned_lines.append(ln)
        chapter["content"] = "\n".join(cleaned_lines).strip()

        return chapter
```

This example demonstrates a typical processor workflow:

* load structured chapter/book dictionaries
* modify specific fields
* return the same structure with cleaned values

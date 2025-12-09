# URL Resolver

NovelKit provides a lightweight URL-resolution utility that converts full
novel-site URLs into structured identifiers such as:

* `site_key`
* `book_id`
* `chapter_id`

This is used by higher-level APIs (e.g., automatic site detection) and can
also be used directly by applications.

---

## Public API

::: novelkit.infra.url_resolver.resolve_book_url

::: novelkit.infra.url_resolver.register_extractor

---

## Example: Adding a Custom Extractor

Suppose a new site uses URLs like:

```
https://book.foo.com/read/123/456.html
```

A custom extractor can be implemented as follows:

```python
import re
from novelkit.infra.url_resolver import register_extractor, BookURLInfo

@register_extractor(["book.foo.com"])
def extract_foo(path: str, query: str) -> BookURLInfo | None:
    # Book info page: /book/123.html
    if m := re.match(r"^/book/(\d+)\.html$", path):
        return {
            "site_key": "foo",
            "book_id": m.group(1),
            "chapter_id": None,
        }

    # Chapter page: /read/123/456.html
    if m := re.match(r"^/read/(\d+)/(\d+)\.html$", path):
        return {
            "site_key": "foo",
            "book_id": m.group(1),
            "chapter_id": m.group(2),
        }

    return None
```

After registering an extractor, resolving URLs becomes straightforward:

```python
from novelkit.infra.url_resolver import resolve_book_url

info = resolve_book_url("https://book.foo.com/read/123/456.html")
print(info)
# {'site_key': 'foo', 'book_id': '123', 'chapter_id': '456'}
```

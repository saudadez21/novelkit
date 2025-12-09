# Plugins

NovelKit provides a modular plugin system for integrating different
novel platforms and extending text-processing features.

A **site plugin** usually defines:

* how to fetch raw pages
* how to parse metadata and chapter text
* optional client-level hooks

All site plugins are located under:

```
plugins/
└── sites/
    └── <site_key>/
        ├── fetcher.py
        ├── parser.py
        └── client.py  (optional)
```

Only the necessary parts need to be implemented.

---

## Site Key Rules

Each site plugin lives under a directory named `<site_key>`.
Site keys follow these rules:

* always normalized to **lowercase**
* if the name begins with a digit, a prefix **`n`** is added
* example: `123abc` -> `n123abc`

These rules ensure that Python namespaces remain valid and that plugin lookup
is consistent across operating systems.

---

## Site Plugin Components

A site plugin may define:

- **Fetcher**: performs HTTP requests and retrieves raw content
- **Parser**: converts HTML/JSON into structured metadata
- **Client** (optional): hooks for site-specific overrides

Typical layout:

```
plugins/
└── sites/
    └── mysite/
        ├── fetcher.py
        ├── parser.py
        └── client.py
```

Plugins are registered using:

```py
@hub.register_fetcher()
@hub.register_parser()
@hub.register_client()
```

Most sites only need a fetcher and a parser.

---

## Processor Plugins

Processors are a separate type of plugin used for:

* content cleanup
* normalization
* enrichment
* formatting adjustments

They operate on parsed `BookInfoDict` and `ChapterDict`, and are placed under:

```
plugins/
└── processors/
    ├── text_cleanup.py
    └── convert_simplified.py
```

Registered via:

```py
@hub.register_processor()
```

---

## Directory Overview

A complete project layout may look like:

```
plugins/
├── sites/
│   └── mysite/
│       ├── fetcher.py
│       ├── parser.py
│       └── client.py
└── processors/
    ├── text_cleanup.py
    └── convert_simplified.py
```

---

## Getting Started

To create a new site plugin:

1. Implement a fetcher
2. Implement a parser
3. (Optionally) implement custom client hooks
4. Register them using the plugin hub decorators

See the following sections for detailed documentation:

* [Fetcher](fetcher.md)
* [Parser](parser.md)
* [Client](client.md)
* [Processor](processor.md)
* [Registry](registry.md)

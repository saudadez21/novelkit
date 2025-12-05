# Chapter Storage

The `novelkit.infra.persistence.chapter_storage` module provides SQLite-based
persistent storage for chapters. It is used by the fetcher and processing
pipeline to store chapter content, track refetch requirements, and retrieve
structured chapter data efficiently.

This storage layer offers:

* A lightweight wrapper around SQLite
* Automatic schema initialization
* In-memory caching of `need_refetch` flags for fast lookups
* CRUD operations for single or multiple chapters
* JSON-encoded metadata fields
* Context-manager support (`with ChapterStorage(...)`)

---

## Reference

::: novelkit.infra.persistence.chapter_storage.ChapterStorage

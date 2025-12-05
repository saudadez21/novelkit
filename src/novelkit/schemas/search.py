from typing import TypedDict


class SearchResult(TypedDict, total=True):
    """Normalized representation of a book search result.

    Attributes:
        site_key: Site identifier for the source site (e.g., "qidian").
        site_name: Human-friendly site name used in UI or logs.
        book_id: Unique identifier for the book on the site.
        book_url: URL to the book's main page.
        cover_url: URL to the book's cover image.
        title: Book title.
        author: Author name.
        description: Short summary or description returned by the site.
        update_date: Human-readable update date string.
        priority: Rank or score indicating result relevance.
    """

    site_key: str
    site_name: str
    book_id: str
    book_url: str
    cover_url: str
    title: str
    author: str
    description: str
    update_date: str
    priority: int

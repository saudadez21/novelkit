from typing import Any, Literal, NotRequired, TypedDict

MediaType = Literal["image", "font", "css", "script", "audio", "other"]


class ChapterDict(TypedDict):
    """Dictionary representation of a parsed chapter.

    Attributes:
        id: Chapter identifier.
        title: Chapter title.
        content: Processed chapter text.
        extra: Additional metadata or site-specific fields.
    """

    id: str
    title: str
    content: str
    extra: dict[str, Any]


class MediaResource(TypedDict):
    """Metadata describing a media resource extracted from chapter content.

    Attributes:
        type: Type of the media resource (image, css, script, etc.).
        paragraph_index: Optional paragraph index where this resource appears.
        range: Optional position range in the original text.
        url: Optional URL of the external media resource.
        base64: Optional base64-encoded content.
        mime: Optional MIME type.
        text: Optional inline text content.
        alt: Alternative text used for images.
        width: Optional width for media elements.
        height: Optional height for media elements.
    """

    type: MediaType
    paragraph_index: NotRequired[int]
    range: NotRequired[dict[str, int]]
    url: NotRequired[str]
    base64: NotRequired[str]
    mime: NotRequired[str]
    text: NotRequired[str]
    alt: NotRequired[str]
    width: NotRequired[int]
    height: NotRequired[int]


class ChapterInfoDict(TypedDict):
    """Basic metadata for a chapter returned by a site.

    Attributes:
        title: Title of the chapter.
        url: Absolute URL of the chapter.
        chapterId: Site-specific chapter identifier.
        accessible: Whether the chapter is accessible without restrictions.
    """

    title: str
    url: str
    chapterId: str
    accessible: bool


class VolumeInfoDict(TypedDict):
    """Metadata describing a volume within a book.

    Attributes:
        volume_name: Name of the volume.
        volume_cover: Optional URL to the volume's cover image.
        volume_intro: Optional volume introduction text.
        chapters: List of chapter metadata belonging to this volume.
    """

    volume_name: str
    volume_cover: NotRequired[str]
    volume_intro: NotRequired[str]
    chapters: list[ChapterInfoDict]


class BookInfoDict(TypedDict):
    """Metadata describing a book retrieved from a site.

    Attributes:
        book_id: Site-specific book identifier.
        book_name: Title of the book.
        author: Author name.
        cover_url: URL of the book cover image.
        update_time: Last update timestamp as a string.
        word_count: Word count string as provided by the site.
        serial_status: Serialization state (ongoing, completed, etc.).
        summary: Brief summary of the book.
        tags: List of book tags.
        volumes: List of volumes containing chapter information.
        extra: Additional metadata or fields not covered by the schema.
        last_checked: Optional Unix timestamp for cache freshness tracking.
    """

    book_id: str
    book_name: str
    author: str
    cover_url: str
    update_time: str
    word_count: str
    serial_status: str
    summary: str
    tags: list[str]
    volumes: list[VolumeInfoDict]
    extra: dict[str, Any]
    last_checked: NotRequired[float]  # Unix timestamp

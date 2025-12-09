from typing import Literal

from novelkit.plugins.base.fetcher import GenericFetcher
from novelkit.plugins.registry import hub


@hub.register_fetcher()
class AkatsukiNovelsFetcher(GenericFetcher):
    site_key = "akatsuki_novels"
    site_name = "暁"
    BASE_URL = "https://www.akatsuki-novels.com"

    USE_PAGINATED_INFO = True

    CHAPTER_PATH = "/stories/view/{chapter_id}/novel_id~{book_id}"

    @classmethod
    def relative_info_url(cls, book_id: str, idx: int) -> str:
        return (
            f"/stories/index/page~{idx}/novel_id~{book_id}"
            if idx > 1
            else f"/stories/index/novel_id~{book_id}"
        )

    def should_continue_pagination(
        self,
        current_html: str,
        next_suffix: str,
        next_idx: int,
        page_type: Literal["info", "catalog", "chapter"],
        book_id: str | None,
        chapter_id: str | None = None,
    ) -> bool:
        if page_type == "info":
            next_patterns = [
                f"/stories/index/page~{next_idx}/novel_id~{book_id}",
                f"/stories/index/novel_id~{book_id}/page~{next_idx}",
            ]
            return any(pat in current_html for pat in next_patterns)

        return False

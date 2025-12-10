from novelkit.plugins.base.fetcher import GenericFetcher
from novelkit.plugins.registry import hub


@hub.register_fetcher()
class AlphapolisFetcher(GenericFetcher):
    site_key = "alphapolis"
    site_name = "アルファポリス"
    BASE_URL = "https://www.alphapolis.co.jp"

    BOOK_ID_REPLACEMENTS = [("-", "/")]

    BOOK_INFO_PATH = "/novel/{book_id}"
    CHAPTER_PATH = "/novel/{book_id}/episode/{chapter_id}"

from __future__ import annotations

from pathlib import Path

import pytest

from novelkit.infra.persistence.chapter_storage import ChapterStorage
from novelkit.schemas import ChapterDict


def _make_chapter(idx: int) -> ChapterDict:
    return ChapterDict(
        id=f"chap{idx}",
        title=f"Title {idx}",
        content=f"Content {idx}",
        extra={"i": idx},
    )


@pytest.fixture
def tmp_storage(tmp_path: Path):
    db_path = tmp_path / "chapters.sqlite"
    store = ChapterStorage(db_path)
    store.connect()

    try:
        yield store
    finally:
        store.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_repr(tmp_storage):
    """Ensure __repr__ returns a meaningful string."""
    r = repr(tmp_storage)
    assert "ChapterStorage" in r
    assert "chapters.sqlite" in r


def test_upsert_and_get_single(tmp_storage):
    chapter = _make_chapter(1)
    tmp_storage.upsert_chapter(chapter)

    got = tmp_storage.get_chapter("chap1")
    assert got is not None
    assert got["title"] == "Title 1"
    assert got["content"] == "Content 1"
    assert got["extra"] == {"i": 1}


def test_get_missing_returns_none(tmp_storage):
    assert tmp_storage.get_chapter("missing") is None


def test_exists_and_need_refetch(tmp_storage):
    chap = _make_chapter(1)
    tmp_storage.upsert_chapter(chap, need_refetch=False)

    assert tmp_storage.exists("chap1")
    assert tmp_storage.need_refetch("chap1") is False

    assert tmp_storage.need_refetch("unknown") is True


def test_upsert_multiple_and_get_many(tmp_storage):
    chapters = [_make_chapter(i) for i in range(3)]
    tmp_storage.upsert_chapters(chapters, need_refetch=True)

    result = tmp_storage.get_chapters(["chap0", "chap1", "chap2", "missing"])
    assert result["chap0"] is not None
    assert result["chap2"]["extra"] == {"i": 2}
    assert result["missing"] is None


def test_existing_dirty_clean_ids(tmp_storage):
    tmp_storage.upsert_chapter(_make_chapter(1), need_refetch=True)
    tmp_storage.upsert_chapter(_make_chapter(2), need_refetch=False)

    assert tmp_storage.existing_ids() == {"chap1", "chap2"}
    assert tmp_storage.dirty_ids() == {"chap1"}
    assert tmp_storage.clean_ids() == {"chap2"}


def test_delete_single(tmp_storage):
    tmp_storage.upsert_chapter(_make_chapter(1))
    assert tmp_storage.exists("chap1")

    assert tmp_storage.delete_chapter("chap1") is True
    assert not tmp_storage.exists("chap1")

    assert tmp_storage.delete_chapter("chap1") is False


def test_delete_multiple(tmp_storage):
    tmp_storage.upsert_chapter(_make_chapter(1))
    tmp_storage.upsert_chapter(_make_chapter(2))
    tmp_storage.upsert_chapter(_make_chapter(3))

    deleted = tmp_storage.delete_chapters(["chap1", "chap3", "missing"])
    assert deleted == 2
    assert tmp_storage.existing_ids() == {"chap2"}


def test_vacuum(tmp_storage):
    """VACUUM should not raise errors."""
    tmp_storage.vacuum()


def test_context_manager(tmp_path: Path):
    """Ensure __enter__ and __exit__ handle connect/close correctly."""
    db_path = tmp_path / "test.sqlite"
    with ChapterStorage(db_path) as store:
        assert store.exists("") is False  # connection is open

    with pytest.raises(RuntimeError):
        _ = store.conn


def test_load_dict_safety(tmp_storage):
    """_load_dict should tolerate bad JSON."""
    assert ChapterStorage._load_dict("not-json") == {}
    assert ChapterStorage._load_dict("") == {}
    assert ChapterStorage._load_dict("null") == {}
    assert ChapterStorage._load_dict('{"a": 1}') == {"a": 1}


def test_connect_is_idempotent(tmp_storage):
    tmp_storage.connect()  # first connect happened in fixture
    tmp_storage.connect()  # should be ignored, no exception
    assert tmp_storage.existing_ids() == set()


def test_close_is_idempotent(tmp_path):
    db = ChapterStorage(tmp_path / "x.sqlite")
    db.connect()

    db.close()
    db.close()


def test_close_without_connect(tmp_path):
    db = ChapterStorage(tmp_path / "x.sqlite")
    db.close()  # should be safe and not raise


def test_upsert_chapters_empty_list(tmp_storage):
    tmp_storage.upsert_chapters([], need_refetch=True)
    assert tmp_storage.existing_ids() == set()


def test_get_chapters_empty_list(tmp_storage):
    assert tmp_storage.get_chapters([]) == {}


def test_delete_chapters_empty_list(tmp_storage):
    assert tmp_storage.delete_chapters([]) == 0
    assert tmp_storage.existing_ids() == set()

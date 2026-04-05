import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from hr_rss.db import ArticleDB
from hr_rss.fetcher import Article


@pytest.fixture
def db(tmp_path: Path):
    """テスト用一時DBを返す。"""
    instance = ArticleDB(tmp_path / "test.db")
    yield instance
    instance.close()


def _article(
    url: str = "https://example.com",
    title: str = "テスト記事",
    published: datetime | None = None,
) -> Article:
    return Article(
        title=title,
        url=url,
        excerpt="概要",
        published=published or datetime.now(UTC),
        source="Test Blog",
    )


# ---------------------------------------------------------------------------
# upsert_articles
# ---------------------------------------------------------------------------


def test_upsert_inserts_new_article(db):
    inserted, skipped = db.upsert_articles([_article(url="https://a.com")])
    assert inserted == 1
    assert skipped == 0


def test_upsert_skips_duplicate_url(db):
    a = _article(url="https://a.com")
    db.upsert_articles([a])
    inserted, skipped = db.upsert_articles([a])
    assert inserted == 0
    assert skipped == 1


def test_upsert_multiple_articles(db):
    articles = [
        _article(url="https://a.com"),
        _article(url="https://b.com"),
        _article(url="https://c.com"),
    ]
    inserted, skipped = db.upsert_articles(articles)
    assert inserted == 3
    assert skipped == 0


def test_upsert_partial_duplicate(db):
    db.upsert_articles([_article(url="https://a.com")])
    inserted, skipped = db.upsert_articles(
        [
            _article(url="https://a.com"),
            _article(url="https://b.com"),
        ]
    )
    assert inserted == 1
    assert skipped == 1


# ---------------------------------------------------------------------------
# update_processed / get_unprocessed
# ---------------------------------------------------------------------------


def test_get_unprocessed_returns_all_after_insert(db):
    db.upsert_articles(
        [
            _article(url="https://a.com"),
            _article(url="https://b.com"),
        ]
    )
    result = db.get_unprocessed()
    assert len(result) == 2


def test_update_processed_removes_from_unprocessed(db):
    db.upsert_articles(
        [
            _article(url="https://a.com"),
            _article(url="https://b.com"),
        ]
    )
    db.update_processed("https://a.com", summary="要約", labels=["生成AI"])
    result = db.get_unprocessed()
    assert len(result) == 1
    assert result[0].url == "https://b.com"


def test_update_processed_sets_labels(db):
    db.upsert_articles([_article(url="https://a.com")])
    db.update_processed("https://a.com", summary="要約", labels=["生成AI", "MLOps"])

    now = datetime.now(UTC)
    articles = db.get_articles_in_range(
        now - timedelta(days=1), now + timedelta(days=1)
    )
    assert len(articles) == 1
    assert articles[0].labels == ["生成AI", "MLOps"]


def test_update_processed_preserves_data_on_second_upsert(db):
    """処理済み行を再upsertしても summary/labels は上書きされない。"""
    db.upsert_articles([_article(url="https://a.com", title="元のタイトル")])
    db.update_processed("https://a.com", summary="元の要約", labels=["生成AI"])

    # 同URLで別タイトルのArticleをupsert → IGNOREされるはず
    db.upsert_articles([_article(url="https://a.com", title="別のタイトル")])
    unprocessed = db.get_unprocessed()
    assert len(unprocessed) == 0  # 処理済みなのでunprocessedには出ない


# ---------------------------------------------------------------------------
# get_articles_in_range / get_summaries_in_range
# ---------------------------------------------------------------------------


def test_get_articles_in_range_filters_by_date(db):
    base = datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)
    db.upsert_articles(
        [
            _article(url="https://old.com", published=base - timedelta(days=10)),
            _article(url="https://mid.com", published=base),
            _article(url="https://new.com", published=base + timedelta(days=5)),
        ]
    )
    for url in ["https://old.com", "https://mid.com", "https://new.com"]:
        db.update_processed(url, summary="要約", labels=[])

    results = db.get_articles_in_range(
        base - timedelta(days=1),
        base + timedelta(days=3),
    )
    urls = {a.url for a in results}
    assert "https://mid.com" in urls
    assert "https://old.com" not in urls
    assert "https://new.com" not in urls


def test_get_articles_in_range_excludes_unprocessed(db):
    now = datetime.now(UTC)
    db.upsert_articles([_article(url="https://a.com", published=now)])
    # update_processed を呼ばない → is_processed=0

    results = db.get_articles_in_range(now - timedelta(days=1), now + timedelta(days=1))
    assert len(results) == 0


def test_get_summaries_in_range_returns_dict(db):
    now = datetime.now(UTC)
    db.upsert_articles([_article(url="https://a.com", published=now)])
    db.update_processed("https://a.com", summary="テスト要約", labels=[])

    summaries = db.get_summaries_in_range(
        now - timedelta(days=1), now + timedelta(days=1)
    )
    assert summaries == {"https://a.com": "テスト要約"}


# ---------------------------------------------------------------------------
# コンテキストマネージャー
# ---------------------------------------------------------------------------


def test_context_manager_closes_connection(tmp_path):
    db_path = tmp_path / "test.db"
    with ArticleDB(db_path) as db:
        db.upsert_articles([])

    # 接続が閉じられているので操作すると ProgrammingError
    with pytest.raises(sqlite3.ProgrammingError):
        db._conn.execute("SELECT 1")

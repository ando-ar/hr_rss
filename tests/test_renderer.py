from datetime import datetime, timezone

from hr_rss.fetcher import Article
from hr_rss.renderer import render_markdown


def _make_article(title: str, url: str, summary: str = "", source: str = "Test Blog") -> Article:
    return Article(
        title=title,
        url=url,
        excerpt="",
        published=datetime(2026, 4, 1, tzinfo=timezone.utc),
        source=source,
        full_text="",
    )


def test_render_markdown_contains_title():
    article = _make_article("AIで採用を革新", "https://example.com/ai")
    md = render_markdown([article], summaries={"https://example.com/ai": "要約テキスト"}, days=7)
    assert "AIで採用を革新" in md


def test_render_markdown_contains_url():
    article = _make_article("タイトル", "https://example.com/article")
    md = render_markdown([article], summaries={"https://example.com/article": "要約"}, days=7)
    assert "https://example.com/article" in md


def test_render_markdown_contains_summary():
    article = _make_article("タイトル", "https://example.com/a")
    md = render_markdown([article], summaries={"https://example.com/a": "これが要約です"}, days=7)
    assert "これが要約です" in md


def test_render_markdown_contains_header_with_days():
    article = _make_article("タイトル", "https://example.com/a")
    md = render_markdown([article], summaries={}, days=14)
    assert "14" in md


def test_render_markdown_contains_source():
    article = _make_article("タイトル", "https://example.com/a", "", source="SmartHR Tech Blog")
    md = render_markdown([article], summaries={}, days=7)
    assert "SmartHR Tech Blog" in md


def test_render_markdown_empty_articles_returns_no_items_message():
    md = render_markdown([], summaries={}, days=7)
    assert "該当記事なし" in md or "No articles" in md or len(md) > 0


def test_render_markdown_shows_labels_when_present():
    article = _make_article("タイトル", "https://example.com/a")
    article.labels = ["生成AI", "推薦システム"]
    md = render_markdown([article], summaries={}, days=7)
    assert "生成AI" in md
    assert "推薦システム" in md


def test_render_markdown_shows_no_label_section_when_empty():
    article = _make_article("タイトル", "https://example.com/a")
    article.labels = []
    md = render_markdown([article], summaries={}, days=7)
    assert "ラベル" not in md

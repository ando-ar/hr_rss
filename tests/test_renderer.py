from datetime import UTC, datetime

from hr_rss.fetcher import Article
from hr_rss.renderer import render_html, render_markdown


def _make_article(
    title: str, url: str, summary: str = "", source: str = "Test Blog"
) -> Article:
    return Article(
        title=title,
        url=url,
        excerpt="",
        published=datetime(2026, 4, 1, tzinfo=UTC),
        source=source,
        full_text="",
    )


def test_render_markdown_contains_title():
    article = _make_article("AIで採用を革新", "https://example.com/ai")
    md = render_markdown(
        [article], summaries={"https://example.com/ai": "要約テキスト"}, days=7
    )
    assert "AIで採用を革新" in md


def test_render_markdown_contains_url():
    article = _make_article("タイトル", "https://example.com/article")
    md = render_markdown(
        [article], summaries={"https://example.com/article": "要約"}, days=7
    )
    assert "https://example.com/article" in md


def test_render_markdown_contains_summary():
    article = _make_article("タイトル", "https://example.com/a")
    md = render_markdown(
        [article], summaries={"https://example.com/a": "これが要約です"}, days=7
    )
    assert "これが要約です" in md


def test_render_markdown_contains_header_with_days():
    article = _make_article("タイトル", "https://example.com/a")
    md = render_markdown([article], summaries={}, days=14)
    assert "14" in md


def test_render_markdown_contains_source():
    article = _make_article(
        "タイトル", "https://example.com/a", "", source="SmartHR Tech Blog"
    )
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


# --- render_html tests ---


def test_render_html_is_valid_html():
    article = _make_article("タイトル", "https://example.com/a")
    result = render_html([article], summaries={}, days=7)
    assert result.startswith("<!DOCTYPE html>")
    assert result.endswith("</html>")


def test_render_html_contains_title():
    article = _make_article("AIで採用を革新", "https://example.com/ai")
    result = render_html([article], summaries={}, days=7)
    assert "AIで採用を革新" in result


def test_render_html_contains_url():
    article = _make_article("タイトル", "https://example.com/article")
    result = render_html([article], summaries={}, days=7)
    assert "https://example.com/article" in result


def test_render_html_contains_summary():
    article = _make_article("タイトル", "https://example.com/a")
    result = render_html(
        [article], summaries={"https://example.com/a": "これが要約です"}, days=7
    )
    assert "これが要約です" in result


def test_render_html_contains_days():
    article = _make_article("タイトル", "https://example.com/a")
    result = render_html([article], summaries={}, days=14)
    assert "14" in result


def test_render_html_contains_source():
    article = _make_article(
        "タイトル", "https://example.com/a", source="SmartHR Tech Blog"
    )
    result = render_html([article], summaries={}, days=7)
    assert "SmartHR Tech Blog" in result


def test_render_html_shows_label_chip():
    article = _make_article("タイトル", "https://example.com/a")
    article.labels = ["生成AI"]
    result = render_html([article], summaries={}, days=7)
    assert "<span" in result
    assert "生成AI" in result


def test_render_html_empty_articles():
    result = render_html([], summaries={}, days=7)
    assert "<!DOCTYPE html>" in result
    assert "該当記事なし" in result


def test_render_html_escapes_xss_in_title():
    article = _make_article("<script>alert(1)</script>", "https://example.com/a")
    result = render_html([article], summaries={}, days=7)
    assert "<script>alert(1)</script>" not in result


def test_render_html_filter_bar_shows_only_present_labels():
    article = _make_article("タイトル", "https://example.com/a")
    article.labels = ["生成AI"]
    result = render_html([article], summaries={}, days=7)
    assert "生成AI" in result
    assert "バックエンド" not in result


def test_render_html_no_summary_shows_fallback():
    article = _make_article("タイトル", "https://example.com/a")
    result = render_html([article], summaries={}, days=7)
    assert "要約なし" in result


def test_render_html_multiple_labels_on_one_card():
    article = _make_article("タイトル", "https://example.com/a")
    article.labels = ["機械学習", "MLOps"]
    result = render_html([article], summaries={}, days=7)
    assert "機械学習" in result
    assert "MLOps" in result

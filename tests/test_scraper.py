from unittest.mock import MagicMock, patch

from hr_rss.scraper import scrape_text

_SAMPLE_HTML = """
<html>
  <body>
    <nav>ナビゲーション</nav>
    <article>
      <h1>記事タイトル</h1>
      <p>本文の段落1。</p>
      <p>本文の段落2。</p>
    </article>
    <footer>フッター</footer>
  </body>
</html>
"""


def _mock_response(html: str, status_code: int = 200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = html
    mock.raise_for_status = MagicMock()
    return mock


def test_scrape_text_extracts_article_body():
    with patch("hr_rss.scraper.httpx.get") as mock_get:
        mock_get.return_value = _mock_response(_SAMPLE_HTML)
        text = scrape_text("https://example.com/article")

    assert "本文の段落1" in text
    assert "本文の段落2" in text


def test_scrape_text_excludes_nav_and_footer():
    with patch("hr_rss.scraper.httpx.get") as mock_get:
        mock_get.return_value = _mock_response(_SAMPLE_HTML)
        text = scrape_text("https://example.com/article")

    assert "ナビゲーション" not in text
    assert "フッター" not in text


def test_scrape_text_returns_empty_string_on_http_error():
    with patch("hr_rss.scraper.httpx.get") as mock_get:
        mock_get.side_effect = Exception("connection error")
        text = scrape_text("https://example.com/article")

    assert text == ""


def test_scrape_text_returns_empty_string_on_non_200():
    with patch("hr_rss.scraper.httpx.get") as mock_get:
        mock = _mock_response("", status_code=404)
        mock.raise_for_status.side_effect = Exception("404")
        mock_get.return_value = mock
        text = scrape_text("https://example.com/article")

    assert text == ""


def test_scrape_text_html_without_article_main_body_returns_empty():
    """article / main / body タグが一切ない HTML を渡したとき空文字列を返すこと"""
    bare_html = "<html><head><title>test</title></head></html>"
    with patch("hr_rss.scraper.httpx.get") as mock_get:
        mock_get.return_value = _mock_response(bare_html)
        text = scrape_text("https://example.com/article")

    assert text == ""

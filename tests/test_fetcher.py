from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from hr_rss.fetcher import Article, fetch_feed, fetch_github_issues


def _make_entry(title: str, link: str, published: datetime, summary: str = "") -> dict:
    return {
        "title": title,
        "link": link,
        "published_parsed": published.timetuple(),
        "summary": summary,
    }


def _mock_http(entries: list[dict], mock_get: MagicMock, mock_parse: MagicMock) -> None:
    """httpx.get と feedparser.parse を一括モック"""
    resp = MagicMock()
    resp.text = "<rss/>"
    resp.raise_for_status = lambda: None
    mock_get.return_value = resp
    mock_parse.return_value = {"entries": entries, "bozo": False}


def test_fetch_feed_returns_articles():
    now = datetime.now(UTC)
    entries = [_make_entry("新しい記事", "https://example.com/new", now)]
    with (
        patch("hr_rss.fetcher.httpx.get") as mock_get,
        patch("hr_rss.fetcher.feedparser.parse") as mock_parse,
    ):
        _mock_http(entries, mock_get, mock_parse)
        result = fetch_feed("https://example.com/feed")

    assert len(result) == 1
    assert result[0].title == "新しい記事"
    assert result[0].url == "https://example.com/new"


def test_fetch_feed_includes_old_articles():
    """日付フィルタは行わないため、古い記事も取得対象になること"""
    old = datetime(2000, 1, 1, tzinfo=UTC)
    entries = [_make_entry("古い記事", "https://example.com/old", old)]
    with (
        patch("hr_rss.fetcher.httpx.get") as mock_get,
        patch("hr_rss.fetcher.feedparser.parse") as mock_parse,
    ):
        _mock_http(entries, mock_get, mock_parse)
        result = fetch_feed("https://example.com/feed")

    assert len(result) == 1
    assert result[0].title == "古い記事"


def test_fetch_feed_returns_article_with_summary():
    now = datetime.now(UTC)
    entries = [
        _make_entry("記事", "https://example.com/a", now, summary="概要テキスト")
    ]
    with (
        patch("hr_rss.fetcher.httpx.get") as mock_get,
        patch("hr_rss.fetcher.feedparser.parse") as mock_parse,
    ):
        _mock_http(entries, mock_get, mock_parse)
        result = fetch_feed("https://example.com/feed")

    assert result[0].excerpt == "概要テキスト"


def test_fetch_feed_skips_article_with_invalid_date():
    """year 0 など time.mktime が ValueError を出す日付の記事はスキップされること"""
    invalid_entry = {
        "title": "不正な日付の記事",
        "link": "https://example.com/bad-date",
        "published_parsed": (0, 1, 1, 0, 0, 0, 0, 1, 0),  # year 0
        "summary": "",
    }
    with (
        patch("hr_rss.fetcher.httpx.get") as mock_get,
        patch("hr_rss.fetcher.feedparser.parse") as mock_parse,
    ):
        _mock_http([invalid_entry], mock_get, mock_parse)
        result = fetch_feed("https://example.com/feed")

    assert result == []


def test_fetch_feed_returns_empty_on_http_error():
    with patch("hr_rss.fetcher.httpx.get") as mock_get:
        mock_get.side_effect = Exception("network error")
        result = fetch_feed("https://example.com/feed")

    assert result == []


def test_fetch_feed_uses_custom_timeout():
    """タイムアウト引数がhttpxに渡されること"""
    now = datetime.now(UTC)
    entries = [_make_entry("記事", "https://example.com/a", now)]
    with (
        patch("hr_rss.fetcher.httpx.get") as mock_get,
        patch("hr_rss.fetcher.feedparser.parse") as mock_parse,
    ):
        _mock_http(entries, mock_get, mock_parse)
        fetch_feed("https://example.com/feed", timeout=10)

    _, kwargs = mock_get.call_args
    assert kwargs.get("timeout") == 10


def test_fetch_feed_skips_on_http_timeout():
    """タイムアウト例外が発生したフィードは空リストを返すこと"""
    with patch("hr_rss.fetcher.httpx.get") as mock_get:
        mock_get.side_effect = Exception("timed out")
        result = fetch_feed("https://example.com/feed", timeout=10)

    assert result == []


def test_fetch_feed_respects_limit():
    """limit を超える記事は切り捨てられ、新しい順に返ること"""
    now = datetime.now(UTC)
    old = datetime(2020, 1, 1, tzinfo=UTC)
    entries = [
        _make_entry("新しい記事", "https://example.com/new", now),
        _make_entry("古い記事", "https://example.com/old", old),
    ]
    with (
        patch("hr_rss.fetcher.httpx.get") as mock_get,
        patch("hr_rss.fetcher.feedparser.parse") as mock_parse,
    ):
        _mock_http(entries, mock_get, mock_parse)
        result = fetch_feed("https://example.com/feed", limit=1)

    assert len(result) == 1
    assert result[0].title == "新しい記事"


def test_article_dataclass_fields():
    article = Article(
        title="タイトル",
        url="https://example.com",
        excerpt="概要",
        published=datetime.now(UTC),
        source="Example Blog",
    )
    assert article.title == "タイトル"
    assert article.source == "Example Blog"


def test_article_has_labels_field_defaulting_to_empty_list():
    article = Article(
        title="タイトル",
        url="https://example.com",
        excerpt="概要",
        published=datetime.now(UTC),
        source="Example Blog",
    )
    assert article.labels == []


def test_article_labels_can_be_set():
    article = Article(
        title="タイトル",
        url="https://example.com",
        excerpt="概要",
        published=datetime.now(UTC),
        source="Example Blog",
        labels=["生成AI", "推薦システム"],
    )
    assert article.labels == ["生成AI", "推薦システム"]


def test_fetch_feed_entry_missing_title_uses_empty_string():
    """エントリに title キーがない場合、空文字列で記事が生成されること"""
    now = datetime.now(UTC)
    entry = {"link": "https://example.com/a", "published_parsed": now.timetuple()}
    with (
        patch("hr_rss.fetcher.httpx.get") as mock_get,
        patch("hr_rss.fetcher.feedparser.parse") as mock_parse,
    ):
        _mock_http([entry], mock_get, mock_parse)
        result = fetch_feed("https://example.com/feed")
    assert len(result) == 1
    assert result[0].title == ""


def test_fetch_feed_entry_missing_link_uses_empty_string():
    """エントリに link キーがない場合、空文字列で記事が生成されること"""
    now = datetime.now(UTC)
    entry = {"title": "タイトル", "published_parsed": now.timetuple()}
    with (
        patch("hr_rss.fetcher.httpx.get") as mock_get,
        patch("hr_rss.fetcher.feedparser.parse") as mock_parse,
    ):
        _mock_http([entry], mock_get, mock_parse)
        result = fetch_feed("https://example.com/feed")
    assert len(result) == 1
    assert result[0].url == ""


def test_fetch_feed_published_parsed_is_none_skips_entry():
    """published_parsed が None のエントリはスキップされること"""
    entry = {
        "title": "タイトル",
        "link": "https://example.com/a",
        "published_parsed": None,
    }
    with (
        patch("hr_rss.fetcher.httpx.get") as mock_get,
        patch("hr_rss.fetcher.feedparser.parse") as mock_parse,
    ):
        _mock_http([entry], mock_get, mock_parse)
        result = fetch_feed("https://example.com/feed")
    assert result == []


# --- fetch_github_issues ---


def _mock_github_http(issues: list[dict], mock_get: MagicMock) -> None:
    resp = MagicMock()
    resp.json.return_value = issues
    resp.raise_for_status = lambda: None
    mock_get.return_value = resp


def _make_issue(
    title: str,
    url: str,
    created_at: datetime,
    body: str = "",
) -> dict:
    return {
        "title": title,
        "html_url": url,
        "body": body,
        "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def test_fetch_github_issues_returns_articles():
    now = datetime.now(UTC)
    issues = [_make_issue("Issue 1", "https://github.com/org/repo/issues/1", now)]
    with patch("hr_rss.fetcher.httpx.get") as mock_get:
        _mock_github_http(issues, mock_get)
        result = fetch_github_issues("https://github.com/org/repo")
    assert len(result) == 1
    assert result[0].title == "Issue 1"
    assert result[0].url == "https://github.com/org/repo/issues/1"


def test_fetch_github_issues_includes_old_issues():
    """日付フィルタは行わないため、古い issue も取得対象になること"""
    old = datetime(2000, 1, 1, tzinfo=UTC)
    issues = [_make_issue("Old Issue", "https://github.com/org/repo/issues/1", old)]
    with patch("hr_rss.fetcher.httpx.get") as mock_get:
        _mock_github_http(issues, mock_get)
        result = fetch_github_issues("https://github.com/org/repo")
    assert len(result) == 1
    assert result[0].title == "Old Issue"


def test_fetch_github_issues_invalid_url_returns_empty():
    result = fetch_github_issues("https://notgithub.com/foo/bar")
    assert result == []


def test_fetch_github_issues_returns_empty_on_http_error():
    with patch("hr_rss.fetcher.httpx.get") as mock_get:
        mock_get.side_effect = Exception("API error")
        result = fetch_github_issues("https://github.com/org/repo")
    assert result == []


def test_fetch_github_issues_stops_when_page_empty():
    with patch("hr_rss.fetcher.httpx.get") as mock_get:
        _mock_github_http([], mock_get)
        result = fetch_github_issues("https://github.com/org/repo")
    assert result == []
    assert mock_get.call_count == 1


def test_fetch_github_issues_uses_body_as_excerpt():
    now = datetime.now(UTC)
    url = "https://github.com/org/repo/issues/1"
    issues = [_make_issue("Issue", url, now, body="本文内容")]
    with patch("hr_rss.fetcher.httpx.get") as mock_get:
        _mock_github_http(issues, mock_get)
        result = fetch_github_issues("https://github.com/org/repo")
    assert result[0].excerpt == "本文内容"


def test_fetch_github_issues_skips_invalid_created_at():
    now = datetime.now(UTC)
    issues = [
        {
            "title": "Bad date",
            "html_url": "https://github.com/org/repo/issues/1",
            "body": "",
            "created_at": "not-a-date",
        },
        _make_issue("Good Issue", "https://github.com/org/repo/issues/2", now),
    ]
    with patch("hr_rss.fetcher.httpx.get") as mock_get:
        _mock_github_http(issues, mock_get)
        result = fetch_github_issues("https://github.com/org/repo")
    assert len(result) == 1
    assert result[0].title == "Good Issue"


def test_fetch_github_issues_respects_limit():
    """limit に達したら pagination を打ち切ること"""
    now = datetime.now(UTC)
    issues = [
        _make_issue(f"Issue {i}", f"https://github.com/org/repo/issues/{i}", now)
        for i in range(5)
    ]
    with patch("hr_rss.fetcher.httpx.get") as mock_get:
        _mock_github_http(issues, mock_get)
        result = fetch_github_issues("https://github.com/org/repo", limit=3)
    assert len(result) == 3

import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import feedparser
import httpx
from loguru import logger

from hr_rss._constants import HTTP_HEADERS

_DEFAULT_TIMEOUT = 10.0
_GITHUB_API_HEADERS = {
    **HTTP_HEADERS,
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _make_cutoff(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


@dataclass
class Article:
    title: str
    url: str
    excerpt: str
    published: datetime
    source: str
    full_text: str = field(default="")
    labels: list[str] = field(default_factory=list)


def fetch_feed(
    url: str, days: int, source: str = "", timeout: float = _DEFAULT_TIMEOUT
) -> list[Article]:
    cutoff = _make_cutoff(days)
    try:
        response = httpx.get(
            url, timeout=timeout, headers=HTTP_HEADERS, follow_redirects=True
        )
        response.raise_for_status()
        feed = feedparser.parse(response.text)
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return []

    articles: list[Article] = []
    for entry in feed.get("entries", []):
        published = _parse_published(entry)
        if published is None or published < cutoff:
            continue
        articles.append(
            Article(
                title=entry.get("title", ""),
                url=entry.get("link", ""),
                excerpt=entry.get("summary", ""),
                published=published,
                source=source,
            )
        )
    return articles


def fetch_github_issues(
    url: str, days: int, source: str = "", timeout: float = _DEFAULT_TIMEOUT
) -> list[Article]:
    """GitHub リポジトリの Issues を Article リストとして返す。

    url には GitHub リポジトリの URL（例: https://github.com/owner/repo）を渡す。
    REST API 経由で取得するため、.atom フィードが無効なリポジトリでも動作する。
    """
    m = re.search(r"github\.com/([^/]+/[^/]+?)(?:\.git)?$", url.rstrip("/"))
    if not m:
        logger.warning(f"Invalid GitHub repo URL: {url}")
        return []

    repo_path = m.group(1)
    api_url = f"https://api.github.com/repos/{repo_path}/issues"
    cutoff = _make_cutoff(days)

    articles: list[Article] = []
    page = 1
    while True:
        try:
            response = httpx.get(
                api_url,
                timeout=timeout,
                headers=_GITHUB_API_HEADERS,
                params={"state": "open", "per_page": 100, "page": page},
            )
            response.raise_for_status()
            issues = response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch GitHub issues {url}: {e}")
            break

        if not issues:
            break

        for issue in issues:
            created_at = issue.get("created_at", "")
            try:
                published = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                continue
            if published < cutoff:
                # Issues は新しい順なのでここで打ち切れる
                return articles

            articles.append(
                Article(
                    title=issue.get("title", ""),
                    url=issue.get("html_url", ""),
                    excerpt=issue.get("body", "") or "",
                    published=published,
                    source=source,
                )
            )

        if len(issues) < 100:
            break
        page += 1

    return articles


def _parse_published(entry: dict) -> datetime | None:
    t = entry.get("published_parsed")
    if t is None:
        return None
    try:
        return datetime.fromtimestamp(time.mktime(t), tz=UTC)
    except (ValueError, OverflowError, OSError):
        return None

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import feedparser
import httpx
from loguru import logger

_DEFAULT_TIMEOUT = 10.0
_HEADERS = {"User-Agent": "hr-rss-bot/1.0 (tech article aggregator)"}


@dataclass
class Article:
    title: str
    url: str
    excerpt: str
    published: datetime
    source: str
    full_text: str = field(default="")
    labels: list[str] = field(default_factory=list)


def fetch_feed(url: str, days: int, source: str = "", timeout: float = _DEFAULT_TIMEOUT) -> list[Article]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        response = httpx.get(url, timeout=timeout, headers=_HEADERS, follow_redirects=True)
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


def _parse_published(entry: dict) -> datetime | None:
    t = entry.get("published_parsed")
    if t is None:
        return None
    try:
        return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None

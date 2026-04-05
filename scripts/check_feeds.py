#!/usr/bin/env python3
"""
feeds.yaml に登録された全フィードへの疎通確認スクリプト。
LLM API は呼ばない。

Usage:
    uv run python scripts/check_feeds.py
    uv run python scripts/check_feeds.py --no-verbose   # NG のみ表示
    uv run python scripts/check_feeds.py --timeout 30
"""

from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import click
import feedparser
import httpx

from hr_rss._constants import HTTP_HEADERS
from hr_rss.config import Config
from hr_rss.fetcher import _GITHUB_API_HEADERS


@dataclass
class FeedCheckResult:
    name: str
    url: str
    ok: bool
    status_code: int | None
    entry_count: int
    bozo: bool
    error: str
    elapsed_ms: float


def _check_rss_feed(name: str, url: str, timeout: float) -> FeedCheckResult:
    t0 = time.monotonic()
    try:
        response = httpx.get(
            url,
            timeout=httpx.Timeout(timeout, connect=5.0),
            headers=HTTP_HEADERS,
            follow_redirects=True,
        )
        response.raise_for_status()
        parsed = feedparser.parse(response.text)
        elapsed_ms = (time.monotonic() - t0) * 1000
        entry_count = len(parsed.get("entries", []))
        bozo = bool(parsed.get("bozo", False))
        error = f"bozo: {parsed.get('bozo_exception', '')}" if bozo else ""
        return FeedCheckResult(
            name=name,
            url=url,
            ok=True,
            status_code=response.status_code,
            entry_count=entry_count,
            bozo=bozo,
            error=error,
            elapsed_ms=elapsed_ms,
        )
    except httpx.HTTPStatusError as e:
        elapsed_ms = (time.monotonic() - t0) * 1000
        return FeedCheckResult(
            name=name,
            url=url,
            ok=False,
            status_code=e.response.status_code,
            entry_count=0,
            bozo=False,
            error=f"HTTP {e.response.status_code}",
            elapsed_ms=elapsed_ms,
        )
    except httpx.TimeoutException:
        elapsed_ms = (time.monotonic() - t0) * 1000
        return FeedCheckResult(
            name=name,
            url=url,
            ok=False,
            status_code=None,
            entry_count=0,
            bozo=False,
            error=f"Timeout after {timeout}s",
            elapsed_ms=elapsed_ms,
        )
    except Exception as e:  # noqa: BLE001
        elapsed_ms = (time.monotonic() - t0) * 1000
        return FeedCheckResult(
            name=name,
            url=url,
            ok=False,
            status_code=None,
            entry_count=0,
            bozo=False,
            error=str(e),
            elapsed_ms=elapsed_ms,
        )


def _check_github_issues(name: str, url: str, timeout: float) -> FeedCheckResult:
    import re

    m = re.search(r"github\.com/([^/]+/[^/]+?)(?:\.git)?$", url.rstrip("/"))
    if not m:
        return FeedCheckResult(
            name=name,
            url=url,
            ok=False,
            status_code=None,
            entry_count=0,
            bozo=False,
            error="Invalid GitHub repo URL",
            elapsed_ms=0,
        )
    api_url = f"https://api.github.com/repos/{m.group(1)}/issues"
    t0 = time.monotonic()
    try:
        response = httpx.get(
            api_url,
            timeout=httpx.Timeout(timeout, connect=5.0),
            headers=_GITHUB_API_HEADERS,
            params={"state": "open", "per_page": 1},
        )
        response.raise_for_status()
        issues = response.json()
        elapsed_ms = (time.monotonic() - t0) * 1000
        # X-RateLimit-Remaining ヘッダーで残りリクエスト数を確認
        remaining = response.headers.get("x-ratelimit-remaining", "?")
        entry_count = len(issues)
        return FeedCheckResult(
            name=name,
            url=url,
            ok=True,
            status_code=response.status_code,
            entry_count=entry_count,
            bozo=False,
            error=f"rate-limit remaining: {remaining}",
            elapsed_ms=elapsed_ms,
        )
    except httpx.HTTPStatusError as e:
        elapsed_ms = (time.monotonic() - t0) * 1000
        return FeedCheckResult(
            name=name,
            url=url,
            ok=False,
            status_code=e.response.status_code,
            entry_count=0,
            bozo=False,
            error=f"HTTP {e.response.status_code}",
            elapsed_ms=elapsed_ms,
        )
    except Exception as e:  # noqa: BLE001
        elapsed_ms = (time.monotonic() - t0) * 1000
        return FeedCheckResult(
            name=name,
            url=url,
            ok=False,
            status_code=None,
            entry_count=0,
            bozo=False,
            error=str(e),
            elapsed_ms=elapsed_ms,
        )


def check_feed(feed: dict, timeout: float) -> FeedCheckResult:
    name = feed.get("name", "")
    url = feed.get("url", "")
    if feed.get("type") == "github_issues":
        return _check_github_issues(name, url, timeout)
    return _check_rss_feed(name, url, timeout)


def check_all_feeds(
    feeds: list[dict],
    timeout: float,
    max_workers: int,
) -> list[FeedCheckResult]:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(lambda f: check_feed(f, timeout), feeds))
    return results


def print_results(results: list[FeedCheckResult], verbose: bool) -> None:
    ok_count = 0
    ng_count = 0
    bozo_count = 0

    for r in results:
        if r.ok and r.bozo:
            bozo_count += 1
            tag = "[OK?]"
        elif r.ok:
            ok_count += 1
            tag = "[OK] "
        else:
            ng_count += 1
            tag = "[NG] "

        if not verbose and r.ok and not r.bozo:
            continue

        status = f"  {r.status_code}" if r.status_code else "  ---"
        entries = f"  {r.entry_count} entries" if r.ok else ""
        elapsed = f"  {r.elapsed_ms:.0f}ms"
        error_part = f"  {r.error}" if r.error else ""
        click.echo(f"{tag} {r.name}{status}{entries}{elapsed}{error_part}")

    total = len(results)
    click.echo(
        f"\nChecked {total} feeds: "
        f"{ok_count} OK, {ng_count} NG, {bozo_count} bozo-warnings"
    )


@click.command()
@click.option("--timeout", default=15.0, show_default=True, help="タイムアウト（秒）")
@click.option("--workers", default=10, show_default=True, help="並列スレッド数")
@click.option("--verbose/--no-verbose", default=True, help="全結果 / NG のみ表示")
@click.option(
    "--profile", default=None, help="プロファイル名（config/profiles/<name>/）"
)
def main(timeout: float, workers: int, verbose: bool, profile: str | None) -> None:
    config = Config(profile=profile)
    label = f"profile={profile}" if profile else "default"
    click.echo(
        f"Checking {len(config.feeds)} feeds [{label}] "
        f"(timeout={timeout}s, workers={workers})...\n"
    )
    results = check_all_feeds(config.feeds, timeout, workers)
    print_results(results, verbose)

    ng_count = sum(1 for r in results if not r.ok)
    sys.exit(1 if ng_count > 0 else 0)


if __name__ == "__main__":
    main()

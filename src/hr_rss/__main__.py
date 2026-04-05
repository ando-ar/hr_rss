from datetime import UTC, datetime
from pathlib import Path

import click
from dotenv import load_dotenv
from loguru import logger

from hr_rss.config import Config
from hr_rss.fetcher import Article, fetch_feed, fetch_github_issues
from hr_rss.filter import is_excluded
from hr_rss.llm import classify_article, get_stats, reset_stats, summarize_and_label
from hr_rss.renderer import render_html, render_markdown
from hr_rss.scraper import scrape_text

load_dotenv()

OUTPUT_DIR = Path("output")


@click.command()
@click.option(
    "--days", default=7, show_default=True, help="何日前までの記事を対象にするか"
)
@click.option(
    "--output",
    default=None,
    help="出力ファイルパス（省略時は output/output_YYYYMMDD.md）",
)
def main(days: int, output: str | None) -> None:
    """HR tech技術記事をRSSから収集し、Markdownにまとめる。"""
    config = Config()
    reset_stats()

    fetchers = {
        "rss": fetch_feed,
        "github_issues": fetch_github_issues,
    }

    # 1. 全フィードから記事を収集
    all_articles: list[Article] = []
    for feed in config.feeds:
        url = feed["url"]
        name = feed.get("name", url)
        logger.info(f"Fetching: {name}")
        feed_type = feed.get("type", "rss")
        fetcher_fn = fetchers.get(feed_type, fetch_feed)
        articles = fetcher_fn(url, days=days, source=name)
        all_articles.extend(articles)

    logger.info(f"Fetched {len(all_articles)} articles total")

    # 2. キーワードフィルタ
    after_keyword = [
        a for a in all_articles if not is_excluded(a.title, config.exclude_keywords)
    ]
    logger.info(f"{len(after_keyword)} articles after keyword filter")

    # 3. LLM Step1: 技術記事か判定
    tech_articles: list[Article] = []
    for article in after_keyword:
        if classify_article(title=article.title, excerpt=article.excerpt):
            tech_articles.append(article)
            logger.info(f"[PASS] {article.title}")
        else:
            logger.info(f"[SKIP] {article.title}")

    logger.info(f"{len(tech_articles)} articles passed LLM classification")

    # 4. LLM Step2: 本文スクレイプ → 要約 + ラベリング
    summaries: dict[str, str] = {}
    for article in tech_articles:
        logger.info(f"Scraping: {article.url}")
        full_text = scrape_text(article.url)
        summary, labels = summarize_and_label(
            title=article.title,
            full_text=full_text or article.excerpt,
            url=article.url,
        )
        summaries[article.url] = summary
        article.labels = labels
        logger.info(f"Labels: {labels}")

    # 5. 出力 (Markdown + HTML)
    md = render_markdown(tech_articles, summaries=summaries, days=days)
    html_content = render_html(tech_articles, summaries=summaries, days=days)

    date_str = datetime.now(UTC).strftime("%Y%m%d")
    if output:
        md_path = Path(output)
        html_path = md_path.with_suffix(".html")
    else:
        OUTPUT_DIR.mkdir(exist_ok=True)
        md_path = OUTPUT_DIR / f"output_{date_str}.md"
        html_path = OUTPUT_DIR / f"output_{date_str}.html"

    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html_content, encoding="utf-8")
    logger.success(f"Written to {md_path} ({len(tech_articles)} articles)")
    logger.success(f"Written to {html_path}")

    _print_summary(
        n_feeds=len(config.feeds),
        n_fetched=len(all_articles),
        n_after_filter=len(after_keyword),
        n_classified=len(tech_articles),
    )


def _print_summary(
    n_feeds: int,
    n_fetched: int,
    n_after_filter: int,
    n_classified: int,
) -> None:
    stats = get_stats()
    total_in = stats["classify_in"] + stats["summarize_in"]
    total_out = stats["classify_out"] + stats["summarize_out"]

    w = 50
    click.echo("")
    click.echo("━" * w)
    click.echo(" 実行サマリー")
    click.echo("─" * w)
    click.echo(f"  フィード取得:         {n_feeds} ソース → {n_fetched} 件")
    click.echo(f"  キーワードフィルタ後: {n_after_filter} 件")
    click.echo(
        f"  LLM 分類 (Step 1):   {n_classified} / {n_after_filter} 件通過"
        f"  [{stats['classify_calls']} calls |"
        f" {stats['classify_in']:,} in / {stats['classify_out']:,} out tok]"
    )
    click.echo(
        f"  LLM 要約 (Step 2):   {n_classified} 件"
        f"  [{stats['summarize_calls']} calls |"
        f" {stats['summarize_in']:,} in / {stats['summarize_out']:,} out tok]"
    )
    click.echo("─" * w)
    click.echo(f"  合計トークン:         {total_in:,} in / {total_out:,} out")
    click.echo("━" * w)
    click.echo("")


if __name__ == "__main__":
    main()

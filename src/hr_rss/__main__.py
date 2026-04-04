from datetime import UTC, datetime
from pathlib import Path

import click
from dotenv import load_dotenv
from loguru import logger

from hr_rss.config import Config
from hr_rss.fetcher import Article, fetch_feed, fetch_github_issues
from hr_rss.filter import is_excluded
from hr_rss.llm import classify_article, summarize_and_label
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

    # 1. 全フィードから記事を収集
    all_articles: list[Article] = []
    for feed in config.feeds:
        url = feed["url"]
        name = feed.get("name", url)
        logger.info(f"Fetching: {name}")
        feed_type = feed.get("type", "rss")
        if feed_type == "github_issues":
            articles = fetch_github_issues(url, days=days, source=name)
        else:
            articles = fetch_feed(url, days=days, source=name)
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


if __name__ == "__main__":
    main()

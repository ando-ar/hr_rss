from datetime import UTC, datetime
from pathlib import Path

import click
from dotenv import load_dotenv
from loguru import logger

from hr_rss.config import Config
from hr_rss.db import ArticleDB, get_db_path
from hr_rss.fetcher import Article, fetch_feed, fetch_github_issues
from hr_rss.filter import is_excluded
from hr_rss.llm import classify_article, get_stats, reset_stats, summarize_and_label
from hr_rss.renderer import render_html, render_markdown
from hr_rss.scraper import scrape_text

load_dotenv()

OUTPUT_DIR = Path("output")


@click.group()
def cli() -> None:
    """HR tech技術記事RSSアグリゲーター。"""


@cli.command("run")
@click.option(
    "--days", default=7, show_default=True, help="何日前までの記事を対象にするか"
)
@click.option(
    "--output",
    default=None,
    help="出力ファイルパス（省略時は output/output_YYYYMMDD.md）",
)
@click.option(
    "--db",
    "db_path",
    default=None,
    help="DBファイルパス（省略時は output/hr_rss.db）",
)
@click.option(
    "--no-db",
    is_flag=True,
    default=False,
    help="DB永続化をスキップして従来通りに動作する",
)
def run_cmd(days: int, output: str | None, db_path: str | None, no_db: bool) -> None:
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

    # 3. DB に保存し、未処理分のみLLM対象とする
    if no_db:
        to_classify = after_keyword
    else:
        resolved_db = Path(db_path) if db_path else get_db_path()
        db = ArticleDB(resolved_db)
        inserted, skipped = db.upsert_articles(after_keyword)
        logger.info(f"DB: {inserted} inserted, {skipped} skipped (already exists)")
        to_classify = db.get_unprocessed()
        logger.info(f"{len(to_classify)} unprocessed articles to classify")

    # 4. LLM Step1: 技術記事か判定
    tech_articles: list[Article] = []
    for article in to_classify:
        if classify_article(title=article.title, excerpt=article.excerpt):
            tech_articles.append(article)
            logger.info(f"[PASS] {article.title}")
        else:
            logger.info(f"[SKIP] {article.title}")
            if not no_db:
                # 技術記事でないと判定されたものも処理済みとしてマーク
                db.update_processed(article.url, summary="", labels=[])

    logger.info(f"{len(tech_articles)} articles passed LLM classification")

    # 5. LLM Step2: 本文スクレイプ → 要約 + ラベリング
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
        if not no_db:
            db.update_processed(
                article.url, summary=summary, labels=labels, full_text=full_text or ""
            )

    # 6. 出力対象：DB使用時はDB経由で日付範囲を取得、no-db時はtech_articles直接
    if no_db:
        output_articles = tech_articles
        output_summaries = summaries
    else:
        now_dt = datetime.now(UTC)
        cutoff_dt = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta

        since_dt = cutoff_dt - timedelta(days=days - 1)
        output_articles = db.get_articles_in_range(since_dt, now_dt)
        output_summaries = db.get_summaries_in_range(since_dt, now_dt)
        db.close()

    # 7. 出力 (Markdown + HTML)
    md = render_markdown(output_articles, summaries=output_summaries, days=days)
    html_content = render_html(output_articles, summaries=output_summaries, days=days)

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
    logger.success(f"Written to {md_path} ({len(output_articles)} articles)")
    logger.success(f"Written to {html_path}")

    _print_summary(
        n_feeds=len(config.feeds),
        n_fetched=len(all_articles),
        n_after_filter=len(after_keyword),
        n_classified=len(tech_articles),
    )


@cli.command("report")
@click.option("--from", "date_from", required=True, help="開始日 YYYY-MM-DD")
@click.option(
    "--to",
    "date_to",
    default=None,
    help="終了日 YYYY-MM-DD（省略時は今日）",
)
@click.option(
    "--output",
    default=None,
    help="出力ファイルパス（省略時は output/report_FROM_TO.md）",
)
@click.option(
    "--db",
    "db_path",
    default=None,
    help="DBファイルパス（省略時は output/hr_rss.db）",
)
def report(
    date_from: str,
    date_to: str | None,
    output: str | None,
    db_path: str | None,
) -> None:
    """過去記事をDBから取得してMarkdown/HTML出力する。"""
    try:
        dt_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError as err:
        raise click.BadParameter(
            f"日付フォーマットが不正です: {date_from}（YYYY-MM-DD形式で指定）"
        ) from err

    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=UTC
            )
        except ValueError as err:
            raise click.BadParameter(
                f"日付フォーマットが不正です: {date_to}（YYYY-MM-DD形式で指定）"
            ) from err
    else:
        dt_to = datetime.now(UTC)
        date_to = dt_to.strftime("%Y-%m-%d")

    resolved_db = Path(db_path) if db_path else get_db_path()
    if not resolved_db.exists():
        raise click.ClickException(f"DBファイルが見つかりません: {resolved_db}")

    with ArticleDB(resolved_db) as db:
        articles = db.get_articles_in_range(dt_from, dt_to)
        summaries = db.get_summaries_in_range(dt_from, dt_to)

    range_label = f"{date_from} 〜 {date_to}"
    md = render_markdown(articles, summaries=summaries, label=range_label)
    html_content = render_html(articles, summaries=summaries, label=range_label)

    if output:
        md_path = Path(output)
        html_path = md_path.with_suffix(".html")
    else:
        OUTPUT_DIR.mkdir(exist_ok=True)
        from_str = date_from.replace("-", "")
        to_str = date_to.replace("-", "")
        md_path = OUTPUT_DIR / f"report_{from_str}_{to_str}.md"
        html_path = OUTPUT_DIR / f"report_{from_str}_{to_str}.html"

    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html_content, encoding="utf-8")
    logger.success(f"Written to {md_path} ({len(articles)} articles)")
    logger.success(f"Written to {html_path}")


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
    cli()

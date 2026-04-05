import os
import shutil
import webbrowser
from datetime import UTC, datetime
from pathlib import Path

import click
from dotenv import load_dotenv
from loguru import logger
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from hr_rss.config import Config
from hr_rss.db import ArticleDB, get_db_path
from hr_rss.fetcher import Article, fetch_feed, fetch_github_issues
from hr_rss.filter import is_excluded
from hr_rss.llm import (
    classify_article,
    get_model,
    get_stats,
    reset_stats,
    summarize_and_label,
)
from hr_rss.renderer import render_html, render_markdown
from hr_rss.scraper import scrape_text

load_dotenv()

OUTPUT_DIR = Path("output")

# モデル別単価 ($/MTok)
_PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (0.80, 4.00),
    "claude-haiku-4-5": (0.80, 4.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-6": (15.00, 75.00),
}


def _validate_env() -> None:
    """APIキーが設定されているか起動前に確認する。"""
    if not os.environ.get("ANTHROPIC_API_KEY", ""):
        raise click.ClickException(
            "ANTHROPIC_API_KEY が設定されていません。\n"
            "  → .env ファイルに ANTHROPIC_API_KEY=sk-ant-... を記入してください\n"
            "  → または: uv run python -m hr_rss setup"
        )


@click.group()
def cli() -> None:
    """HR tech技術記事RSSアグリゲーター。"""


@cli.command("setup")
def setup_cmd() -> None:
    """初回セットアップ（APIキー設定・設定ファイル初期化）。"""
    # プロジェクトルートを探す
    project_root = Path.cwd()
    for parent in [Path.cwd(), *Path.cwd().parents]:
        if (parent / "pyproject.toml").exists():
            project_root = parent
            break

    click.echo("")
    click.echo("━" * 50)
    click.echo(" HR RSS セットアップ")
    click.echo("━" * 50)

    # .env の作成
    env_path = project_root / ".env"
    if env_path.exists():
        click.echo(f"✓ .env は既に存在します: {env_path}")
    else:
        api_key = click.prompt(
            "\nAnthropicのAPIキーを入力してください\n"
            "  (取得: https://console.anthropic.com/)\n"
            "  APIキー",
            hide_input=True,
        )
        env_path.write_text(f"ANTHROPIC_API_KEY={api_key}\n", encoding="utf-8")
        click.echo(f"✓ .env を作成しました: {env_path}")

    # 設定ファイルのコピー
    click.echo("")
    config_dir = project_root / "config"
    for name in ["feeds.yaml", "exclude_keywords.yaml", "labels.yaml", "prompts.yaml"]:
        target = config_dir / name
        sample = config_dir / name.replace(".yaml", ".sample.yaml")
        if target.exists():
            click.echo(f"✓ config/{name} は既に存在します")
        elif sample.exists():
            shutil.copy(sample, target)
            click.echo(f"✓ config/{name} を作成しました（サンプルからコピー）")
        else:
            click.echo(f"  config/{name}.sample.yaml が見つかりません（スキップ）")

    click.echo("")
    click.echo("━" * 50)
    click.echo(" セットアップ完了！以下のコマンドで実行できます：")
    click.echo("   uv run python -m hr_rss run")
    click.echo("━" * 50)
    click.echo("")


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
@click.option(
    "--open/--no-open",
    "open_browser",
    default=True,
    help="生成後にブラウザで自動オープン（デフォルト: ON）",
)
def run_cmd(
    days: int,
    output: str | None,
    db_path: str | None,
    no_db: bool,
    open_browser: bool,
) -> None:
    """HR tech技術記事をRSSから収集し、Markdownにまとめる。"""
    _validate_env()
    config = Config()
    reset_stats()

    fetchers = {
        "rss": fetch_feed,
        "github_issues": fetch_github_issues,
    }

    # 1. 全フィードから記事を収集
    all_articles: list[Article] = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task("フィード取得中...", total=len(config.feeds))
        for feed in config.feeds:
            url = feed["url"]
            name = feed.get("name", url)
            progress.update(task, description=f"取得中: {name}")
            feed_type = feed.get("type", "rss")
            fetcher_fn = fetchers.get(feed_type, fetch_feed)
            articles = fetcher_fn(url, days=days, source=name)
            all_articles.extend(articles)
            progress.advance(task)

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
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task("LLM 分類中...", total=len(to_classify))
        for article in to_classify:
            progress.update(task, description=f"分類中: {article.title[:40]}...")
            if classify_article(title=article.title, excerpt=article.excerpt):
                tech_articles.append(article)
                logger.info(f"[PASS] {article.title}")
            else:
                logger.info(f"[SKIP] {article.title}")
                if not no_db:
                    db.update_processed(article.url, summary="", labels=[])
            progress.advance(task)

    logger.info(f"{len(tech_articles)} articles passed LLM classification")

    # 5. LLM Step2: 本文スクレイプ → 要約 + ラベリング
    summaries: dict[str, str] = {}
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task("LLM 要約中...", total=len(tech_articles))
        for article in tech_articles:
            progress.update(task, description=f"要約中: {article.title[:40]}...")
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
                    article.url,
                    summary=summary,
                    labels=labels,
                    full_text=full_text or "",
                )
            progress.advance(task)

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

    if open_browser:
        webbrowser.open(html_path.resolve().as_uri())


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
@click.option(
    "--open/--no-open",
    "open_browser",
    default=True,
    help="生成後にブラウザで自動オープン（デフォルト: ON）",
)
def report(
    date_from: str,
    date_to: str | None,
    output: str | None,
    db_path: str | None,
    open_browser: bool,
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

    if open_browser:
        webbrowser.open(html_path.resolve().as_uri())


def _print_summary(
    n_feeds: int,
    n_fetched: int,
    n_after_filter: int,
    n_classified: int,
) -> None:
    stats = get_stats()
    total_in = stats["classify_in"] + stats["summarize_in"]
    total_out = stats["classify_out"] + stats["summarize_out"]

    model = get_model()
    price_in, price_out = _PRICING.get(model, (0.0, 0.0))
    estimated_cost = (total_in * price_in + total_out * price_out) / 1_000_000

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
    if price_in > 0:
        click.echo(f"  推定コスト:           ${estimated_cost:.4f}（概算、{model}）")
    click.echo("━" * w)
    click.echo("")


if __name__ == "__main__":
    cli()

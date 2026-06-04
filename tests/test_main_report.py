"""report コマンドのテスト。

report コマンドは OUTPUT_DIR 以下の hr_rss_*.db を自動スキャンして HTML を出力する。
各テストでは monkeypatch で OUTPUT_DIR を tmp_path に向け、
hr_rss_test.db をそこに配置してコマンドを実行する。
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

from hr_rss.__main__ import report
from hr_rss.db import ArticleDB
from hr_rss.fetcher import Article


def _make_article(
    url: str = "https://example.com",
    title: str = "テスト記事",
    published: datetime | None = None,
) -> Article:
    return Article(
        title=title,
        url=url,
        excerpt="概要",
        published=published or datetime.now(UTC),
        source="Test Blog",
    )


@pytest.fixture
def populated_db(tmp_path: Path) -> Path:
    """処理済み記事が入ったDBを hr_rss_test.db として返す。

    ファイル名は _collect_profile_dbs() の glob パターン (hr_rss_*.db) に合わせる。
    """
    db_path = tmp_path / "hr_rss_test.db"
    now = datetime(2026, 4, 5, 12, 0, 0, tzinfo=UTC)
    articles = [
        _make_article(
            url="https://a.com", title="生成AI記事", published=now - timedelta(days=1)
        ),
        _make_article(
            url="https://b.com", title="MLOps記事", published=now - timedelta(days=3)
        ),
        _make_article(
            url="https://old.com", title="古い記事", published=now - timedelta(days=60)
        ),
    ]
    with ArticleDB(db_path) as db:
        db.upsert_articles(articles)
        db.update_processed("https://a.com", summary="AI要約", labels=["生成AI"])
        db.update_processed("https://b.com", summary="MLOps要約", labels=["MLOps"])
        db.update_processed("https://old.com", summary="古い要約", labels=[])
    return db_path


def test_report_outputs_html(tmp_path, populated_db, monkeypatch):
    """report コマンドが HTML を出力すること。"""
    import hr_rss.__main__ as m

    monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        report, ["--from", "2026-04-01", "--to", "2026-04-05", "--no-open"]
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "report.html").exists()


def test_report_filters_by_date_range(tmp_path, populated_db, monkeypatch):
    """指定期間外の古い記事は出力に含まれない。"""
    import hr_rss.__main__ as m

    monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)

    runner = CliRunner()
    runner.invoke(report, ["--from", "2026-04-01", "--to", "2026-04-05", "--no-open"])
    content = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "生成AI記事" in content
    assert "MLOps記事" in content
    assert "古い記事" not in content


def test_report_includes_labels(tmp_path, populated_db, monkeypatch):
    """記事ラベルが出力 HTML に含まれること。"""
    import hr_rss.__main__ as m

    monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)

    runner = CliRunner()
    runner.invoke(report, ["--from", "2026-04-01", "--to", "2026-04-05", "--no-open"])
    content = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "生成AI" in content
    assert "MLOps" in content


def test_report_uses_date_range_label_in_header(tmp_path, populated_db, monkeypatch):
    """日付範囲ラベルがヘッダーに使われ「過去N日」は表示されないこと。"""
    import hr_rss.__main__ as m

    monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)

    runner = CliRunner()
    runner.invoke(report, ["--from", "2026-04-01", "--to", "2026-04-05", "--no-open"])
    content = (tmp_path / "report.html").read_text(encoding="utf-8")
    assert "2026-04-01 〜 2026-04-05" in content
    assert "過去" not in content


def test_report_missing_db_exits_with_error(tmp_path, monkeypatch):
    """OUTPUT_DIR に hr_rss_*.db が存在しない場合はエラー終了すること。"""
    import hr_rss.__main__ as m

    monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path)  # empty → no matching DBs

    runner = CliRunner()
    result = runner.invoke(report, ["--from", "2026-04-01"])
    assert result.exit_code != 0


def test_report_default_output_path(tmp_path, monkeypatch):
    """--output 省略時に OUTPUT_DIR/report.html が生成されること。"""
    import hr_rss.__main__ as m

    output_dir = tmp_path / "output"
    output_dir.mkdir()
    monkeypatch.setattr(m, "OUTPUT_DIR", output_dir)

    # DB を OUTPUT_DIR 直下に hr_rss_*.db 形式で配置
    db_path = output_dir / "hr_rss_test.db"
    now = datetime(2026, 4, 5, 12, 0, 0, tzinfo=UTC)
    with ArticleDB(db_path) as db:
        db.upsert_articles(
            [_make_article(url="https://x.com", published=now - timedelta(days=1))]
        )
        db.update_processed("https://x.com", summary="要約", labels=[])

    runner = CliRunner()
    result = runner.invoke(
        report, ["--from", "2026-04-01", "--to", "2026-04-05", "--no-open"]
    )
    assert result.exit_code == 0, result.output
    assert (output_dir / "report.html").exists()

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
    """処理済み記事が入ったDBパスを返す。"""
    db_path = tmp_path / "test.db"
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


def test_report_outputs_md_and_html(tmp_path, populated_db):
    runner = CliRunner()
    result = runner.invoke(
        report,
        [
            "--from",
            "2026-04-01",
            "--to",
            "2026-04-05",
            "--db",
            str(populated_db),
            "--output",
            str(tmp_path / "report.md"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "report.html").exists()


def test_report_filters_by_date_range(tmp_path, populated_db):
    """指定期間外の古い記事は出力に含まれない。"""
    output_path = tmp_path / "report.md"
    runner = CliRunner()
    runner.invoke(
        report,
        [
            "--from",
            "2026-04-01",
            "--to",
            "2026-04-05",
            "--db",
            str(populated_db),
            "--output",
            str(output_path),
        ],
    )
    content = output_path.read_text(encoding="utf-8")
    assert "生成AI記事" in content
    assert "MLOps記事" in content
    assert "古い記事" not in content


def test_report_includes_labels(tmp_path, populated_db):
    output_path = tmp_path / "report.md"
    runner = CliRunner()
    runner.invoke(
        report,
        [
            "--from",
            "2026-04-01",
            "--to",
            "2026-04-05",
            "--db",
            str(populated_db),
            "--output",
            str(output_path),
        ],
    )
    content = output_path.read_text(encoding="utf-8")
    assert "生成AI" in content
    assert "MLOps" in content


def test_report_uses_label_in_header(tmp_path, populated_db):
    output_path = tmp_path / "report.md"
    runner = CliRunner()
    runner.invoke(
        report,
        [
            "--from",
            "2026-04-01",
            "--to",
            "2026-04-05",
            "--db",
            str(populated_db),
            "--output",
            str(output_path),
        ],
    )
    content = output_path.read_text(encoding="utf-8")
    # daysではなく日付範囲ラベルが使われる
    assert "2026-04-01 〜 2026-04-05" in content
    assert "過去" not in content


def test_report_missing_db_exits_with_error(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        report,
        [
            "--from",
            "2026-04-01",
            "--db",
            str(tmp_path / "nonexistent.db"),
        ],
    )
    assert result.exit_code != 0


def test_report_default_output_path(tmp_path, populated_db, monkeypatch):
    """--output 省略時に output/report_FROM_TO.md が生成される。"""
    monkeypatch.chdir(tmp_path)
    # OUTPUT_DIR を tmp_path 内に向ける
    import hr_rss.__main__ as m

    monkeypatch.setattr(m, "OUTPUT_DIR", tmp_path / "output")

    runner = CliRunner()
    result = runner.invoke(
        report,
        [
            "--from",
            "2026-04-01",
            "--to",
            "2026-04-05",
            "--db",
            str(populated_db),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "output" / "report_20260401_20260405.md").exists()

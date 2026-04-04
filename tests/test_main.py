from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from hr_rss.__main__ import main
from hr_rss.fetcher import Article


def _make_article(title: str = "AI記事", url: str = "https://example.com") -> Article:
    return Article(
        title=title,
        url=url,
        excerpt="概要",
        published=datetime.now(timezone.utc),
        source="Test Blog",
    )


def test_main_runs_without_error(tmp_path):
    with (
        patch("hr_rss.__main__.fetch_feed", return_value=[]),
        patch("hr_rss.__main__.Config") as mock_config_cls,
        patch("hr_rss.__main__.OUTPUT_DIR", tmp_path),
    ):
        mock_config = MagicMock()
        mock_config.feeds = [{"url": "https://example.com/feed", "name": "Test"}]
        mock_config.exclude_keywords = []
        mock_config_cls.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(main, ["--days", "7"])

    assert result.exit_code == 0


def test_main_writes_output_to_output_dir(tmp_path):
    with (
        patch("hr_rss.__main__.fetch_feed", return_value=[]),
        patch("hr_rss.__main__.Config") as mock_config_cls,
        patch("hr_rss.__main__.OUTPUT_DIR", tmp_path),
    ):
        mock_config = MagicMock()
        mock_config.feeds = []
        mock_config.exclude_keywords = []
        mock_config_cls.return_value = mock_config

        runner = CliRunner()
        runner.invoke(main, ["--days", "7"])

    assert any(tmp_path.iterdir())


def test_main_explicit_output_path(tmp_path):
    output_path = tmp_path / "report.md"
    with (
        patch("hr_rss.__main__.fetch_feed", return_value=[]),
        patch("hr_rss.__main__.Config") as mock_config_cls,
        patch("hr_rss.__main__.OUTPUT_DIR", tmp_path),
    ):
        mock_config = MagicMock()
        mock_config.feeds = []
        mock_config.exclude_keywords = []
        mock_config_cls.return_value = mock_config

        runner = CliRunner()
        runner.invoke(main, ["--days", "7", "--output", str(output_path)])

    assert output_path.exists()


def test_main_labels_are_set_on_articles(tmp_path):
    tech = _make_article(title="LLMで採用スクリーニング", url="https://example.com/2")

    with (
        patch("hr_rss.__main__.fetch_feed", return_value=[tech]),
        patch("hr_rss.__main__.classify_article", return_value=True),
        patch("hr_rss.__main__.summarize_and_label", return_value=("要約", ["生成AI"])),
        patch("hr_rss.__main__.scrape_text", return_value="本文"),
        patch("hr_rss.__main__.Config") as mock_config_cls,
        patch("hr_rss.__main__.OUTPUT_DIR", tmp_path),
    ):
        mock_config = MagicMock()
        mock_config.feeds = [{"url": "https://example.com/feed", "name": "Test"}]
        mock_config.exclude_keywords = []
        mock_config_cls.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(main, ["--days", "7"])

    assert result.exit_code == 0
    output_files = list(tmp_path.iterdir())
    assert len(output_files) == 1
    content = output_files[0].read_text()
    assert "生成AI" in content

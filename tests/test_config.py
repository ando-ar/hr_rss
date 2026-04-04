from pathlib import Path

import pytest

from hr_rss.config import Config

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_config_loads_feed_urls(tmp_path):
    feeds_yaml = tmp_path / "feeds.yaml"
    feeds_yaml.write_text(
        "feeds:\n  - url: https://example.com/feed\n    name: Example\n"
    )

    config = Config(feeds_path=feeds_yaml)

    assert len(config.feeds) == 1
    assert config.feeds[0]["url"] == "https://example.com/feed"
    assert config.feeds[0]["name"] == "Example"


def test_config_loads_multiple_feeds(tmp_path):
    feeds_yaml = tmp_path / "feeds.yaml"
    feeds_yaml.write_text(
        "feeds:\n"
        "  - url: https://a.com/feed\n    name: A\n"
        "  - url: https://b.com/feed\n    name: B\n"
    )

    config = Config(feeds_path=feeds_yaml)

    assert len(config.feeds) == 2


def test_config_has_exclude_keywords():
    config = Config()

    assert len(config.exclude_keywords) > 0
    assert any("資金調達" in kw for kw in config.exclude_keywords)
    assert any("勉強会" in kw for kw in config.exclude_keywords)


def test_config_raises_if_feeds_file_not_found():
    with pytest.raises(FileNotFoundError):
        Config(feeds_path=Path("/nonexistent/feeds.yaml"))


def test_config_feeds_is_null_in_yaml(tmp_path):
    """feeds: null の YAML を読んでも AttributeError にならず空リストを返すこと"""
    feeds_yaml = tmp_path / "feeds.yaml"
    feeds_yaml.write_text("feeds: null\n")
    config = Config(feeds_path=feeds_yaml)
    assert config.feeds == []


def test_config_empty_feeds_list(tmp_path):
    """feeds: [] の YAML を読んだとき空リストを返すこと"""
    feeds_yaml = tmp_path / "feeds.yaml"
    feeds_yaml.write_text("feeds: []\n")
    config = Config(feeds_path=feeds_yaml)
    assert config.feeds == []


def test_config_raises_if_exclude_keywords_file_not_found(tmp_path):
    """exclude_keywords.yaml が存在しない場合 FileNotFoundError を送出すること"""
    feeds_yaml = tmp_path / "feeds.yaml"
    feeds_yaml.write_text("feeds: []\n")
    # config_dir を存在するが exclude_keywords.yaml を含まないディレクトリに向ける
    with pytest.raises(FileNotFoundError):
        Config(config_dir=tmp_path, feeds_path=feeds_yaml)

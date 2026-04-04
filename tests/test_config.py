from pathlib import Path

import pytest

from hr_rss.config import Config


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_config_loads_feed_urls(tmp_path):
    feeds_yaml = tmp_path / "feeds.yaml"
    feeds_yaml.write_text("feeds:\n  - url: https://example.com/feed\n    name: Example\n")

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

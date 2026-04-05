"""共通 pytest フィクスチャ

使い方:
    テスト内で引数名を宣言するだけで自動注入される。
    例) def test_something(tmp_data_dir): ...

Hypothesis プロファイル:
    dev  (デフォルト): max_examples=200  ローカル開発用
    ci                : max_examples=50   CI 向け高速版
    fast              : max_examples=20   スモークテスト用

    切り替え:
        uv run pytest --hypothesis-profile=ci
"""

import os
from datetime import UTC, datetime

import pytest
from hypothesis import HealthCheck, settings

from hr_rss.fetcher import Article

# ---------------------------------------------------------------------------
# Hypothesis プロファイル
# ---------------------------------------------------------------------------
settings.register_profile(
    "dev",
    max_examples=200,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile(
    "ci",
    max_examples=50,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile(
    "fast",
    max_examples=20,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))


# ---------------------------------------------------------------------------
# ディレクトリ
# ---------------------------------------------------------------------------
@pytest.fixture
def tmp_data_dir(tmp_path):
    """一時作業ディレクトリ。"""
    return tmp_path


# ---------------------------------------------------------------------------
# Articleファクトリー
# ---------------------------------------------------------------------------
@pytest.fixture
def make_article():
    """Article インスタンスを生成するファクトリー関数を返す。"""

    def _make(
        title: str = "テスト記事",
        url: str = "https://example.com",
        published: datetime | None = None,
        **kwargs,
    ) -> Article:
        return Article(
            title=title,
            url=url,
            excerpt="概要テキスト",
            published=published or datetime.now(UTC),
            source="Test Blog",
            **kwargs,
        )

    return _make

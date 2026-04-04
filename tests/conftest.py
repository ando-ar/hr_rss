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

import pytest
from hypothesis import HealthCheck, settings

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

"""conftest.py のフィクスチャ仕様テスト。

フィクスチャそのものが正しく動くことを保証する。
"""

from pathlib import Path


# ---------------------------------------------------------------------------
# tmp_data_dir
# ---------------------------------------------------------------------------
def test_tmp_data_dir_is_directory(tmp_data_dir):
    assert isinstance(tmp_data_dir, Path)
    assert tmp_data_dir.is_dir()

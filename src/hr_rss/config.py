from pathlib import Path

import yaml


def _find_config_dir() -> Path:
    """プロジェクトルートの config/ ディレクトリを返す。

    実行時の CWD から pyproject.toml を探して上位に辿り、
    見つかればその隣の config/ を返す。見つからなければ CWD/config/ を返す。
    """
    for parent in [Path.cwd(), *Path.cwd().parents]:
        if (parent / "pyproject.toml").exists():
            return parent / "config"
    return Path.cwd() / "config"


def _resolve_config_file(dir: Path, name: str) -> Path:
    """ユーザー独自ファイル → サンプルファイルの順で解決する。

    ``dir / name`` が存在すればそれを返す。なければ
    ``dir / <stem>.sample.yaml`` を試みる。どちらも存在しない場合は
    FileNotFoundError を送出する。
    """
    plain = dir / name
    if plain.exists():
        return plain
    sample = dir / name.replace(".yaml", ".sample.yaml")
    if sample.exists():
        return sample
    raise FileNotFoundError(f"config file not found: {plain} (also tried {sample})")


class Config:
    def __init__(
        self,
        config_dir: Path | None = None,
        feeds_path: Path | None = None,
    ) -> None:
        self._dir = config_dir if config_dir is not None else _find_config_dir()

        resolved_feeds_path = (
            feeds_path
            if feeds_path is not None
            else _resolve_config_file(self._dir, "feeds.yaml")
        )
        with resolved_feeds_path.open() as f:
            data = yaml.safe_load(f)
        self.feeds: list[dict] = (data or {}).get("feeds") or []

        exclude_path = _resolve_config_file(self._dir, "exclude_keywords.yaml")
        with exclude_path.open() as f:
            kw_data = yaml.safe_load(f)
        self.exclude_keywords: list[str] = kw_data.get("exclude_keywords", [])

    @property
    def config_dir(self) -> Path:
        return self._dir

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


class Config:
    def __init__(
        self,
        config_dir: Path | None = None,
        feeds_path: Path | None = None,
    ) -> None:
        self._dir = config_dir if config_dir is not None else _find_config_dir()

        resolved_feeds_path = (
            feeds_path if feeds_path is not None else self._dir / "feeds.yaml"
        )
        if not resolved_feeds_path.exists():
            raise FileNotFoundError(f"feeds file not found: {resolved_feeds_path}")
        with resolved_feeds_path.open() as f:
            data = yaml.safe_load(f)
        self.feeds: list[dict] = data.get("feeds", [])

        exclude_path = self._dir / "exclude_keywords.yaml"
        if not exclude_path.exists():
            raise FileNotFoundError(f"exclude_keywords file not found: {exclude_path}")
        with exclude_path.open() as f:
            kw_data = yaml.safe_load(f)
        self.exclude_keywords: list[str] = kw_data.get("exclude_keywords", [])

    @property
    def config_dir(self) -> Path:
        return self._dir

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


def _resolve_with_fallback(profile_dir: Path, base_dir: Path, name: str) -> Path:
    """プロファイルdir → ベースdir の順で設定ファイルを解決する。

    profile_dir に name（またはそのサンプル）があればそれを優先し、
    なければ base_dir にフォールバックする。
    """
    for d in (profile_dir, base_dir):
        plain = d / name
        if plain.exists():
            return plain
        sample = d / name.replace(".yaml", ".sample.yaml")
        if sample.exists():
            return sample
    raise FileNotFoundError(
        f"config file not found: {name} (tried {profile_dir} and {base_dir})"
    )


class Config:
    def __init__(
        self,
        config_dir: Path | None = None,
        feeds_path: Path | None = None,
        profile: str | None = None,
    ) -> None:
        self._dir = config_dir if config_dir is not None else _find_config_dir()
        self.profile_name: str | None = profile

        if profile is not None:
            profile_dir = self._dir / "profiles" / profile
            resolve = lambda name: _resolve_with_fallback(profile_dir, self._dir, name)  # noqa: E731
        else:
            resolve = lambda name: _resolve_config_file(self._dir, name)  # noqa: E731

        resolved_feeds_path = (
            feeds_path if feeds_path is not None else resolve("feeds.yaml")
        )
        with resolved_feeds_path.open() as f:
            data = yaml.safe_load(f)
        self.feeds: list[dict] = (data or {}).get("feeds") or []

        exclude_path = resolve("exclude_keywords.yaml")
        with exclude_path.open() as f:
            kw_data = yaml.safe_load(f)
        self.exclude_keywords: list[str] = kw_data.get("exclude_keywords", [])

    @property
    def config_dir(self) -> Path:
        """llm.py が labels/prompts を読む際に使うdirを返す。

        プロファイル指定時はプロファイルdirを返し、llm.py 側でも
        _resolve_with_fallback によるフォールバックが効くようにする。
        """
        if self.profile_name is not None:
            return self._dir / "profiles" / self.profile_name
        return self._dir

    @property
    def base_dir(self) -> Path:
        """ベースの config/ ディレクトリを返す（フォールバック先）。"""
        return self._dir

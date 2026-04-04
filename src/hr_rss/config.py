from pathlib import Path

import yaml

_DEFAULT_FEEDS_PATH = Path(__file__).parent / "feeds.yaml"

_EXCLUDE_KEYWORDS: list[str] = [
    # 日本語
    "資金調達",
    "シリーズ",
    "提携",
    "業務提携",
    "資本提携",
    "合併",
    "買収",
    "勉強会",
    "イベント",
    "セミナー",
    "カンファレンス",
    "登壇",
    "採用",
    "求人",
    "インターン",
    "表彰",
    "受賞",
    "上場",
    "IPO",
    # English
    "funding",
    "series a",
    "series b",
    "series c",
    "raises",
    "raised",
    "partnership",
    "partners with",
    "acquisition",
    "acquires",
    "merger",
    "meetup",
    "webinar",
    "hiring",
    "job opening",
    "we're hiring",
]


class Config:
    def __init__(self, feeds_path: Path | None = None) -> None:
        path = feeds_path if feeds_path is not None else _DEFAULT_FEEDS_PATH
        if not path.exists():
            raise FileNotFoundError(f"feeds file not found: {path}")
        with path.open() as f:
            data = yaml.safe_load(f)
        self.feeds: list[dict] = data.get("feeds", [])
        self.exclude_keywords: list[str] = _EXCLUDE_KEYWORDS

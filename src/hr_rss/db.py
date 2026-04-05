import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from hr_rss.fetcher import Article

_SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    url          TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    excerpt      TEXT NOT NULL DEFAULT '',
    published    TEXT NOT NULL,
    source       TEXT NOT NULL DEFAULT '',
    full_text    TEXT NOT NULL DEFAULT '',
    labels       TEXT NOT NULL DEFAULT '[]',
    summary      TEXT NOT NULL DEFAULT '',
    is_processed INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published);
"""


def get_db_path(profile: str | None = None) -> Path:
    """プロジェクトルートの output/hr_rss[_profile].db を返す。"""
    db_name = f"hr_rss_{profile}.db" if profile else "hr_rss.db"
    for parent in [Path.cwd(), *Path.cwd().parents]:
        if (parent / "pyproject.toml").exists():
            output_dir = parent / "output"
            output_dir.mkdir(exist_ok=True)
            return output_dir / db_name
    output_dir = Path.cwd() / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir / db_name


def _row_to_article(row: sqlite3.Row) -> Article:
    published_str: str = row["published"]
    published = datetime.fromisoformat(published_str)
    if published.tzinfo is None:
        published = published.replace(tzinfo=UTC)
    labels: list[str] = json.loads(row["labels"])
    return Article(
        title=row["title"],
        url=row["url"],
        excerpt=row["excerpt"],
        published=published,
        source=row["source"],
        full_text=row["full_text"],
        labels=labels,
    )


class ArticleDB:
    def __init__(self, db_path: Path) -> None:
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def __enter__(self) -> "ArticleDB":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    def upsert_articles(self, articles: list[Article]) -> tuple[int, int]:
        """未処理記事をINSERT OR IGNORE。戻り値: (inserted, skipped)"""
        inserted = 0
        skipped = 0
        cur = self._conn.cursor()
        for a in articles:
            cur.execute(
                """
                INSERT OR IGNORE INTO articles (url, title, excerpt, published, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (a.url, a.title, a.excerpt, a.published.isoformat(), a.source),
            )
            if cur.rowcount == 1:
                inserted += 1
            else:
                skipped += 1
        self._conn.commit()
        return inserted, skipped

    def update_processed(
        self,
        url: str,
        summary: str,
        labels: list[str],
        full_text: str = "",
    ) -> None:
        """LLM処理完了後にsummary/labels/full_textを更新し、is_processed=1にする。"""
        self._conn.execute(
            """
            UPDATE articles
            SET summary = ?, labels = ?, full_text = ?, is_processed = 1
            WHERE url = ?
            """,
            (summary, json.dumps(labels, ensure_ascii=False), full_text, url),
        )
        self._conn.commit()

    def get_unprocessed(self) -> list[Article]:
        """is_processed=0 の全記事を返す。"""
        cur = self._conn.execute(
            "SELECT * FROM articles WHERE is_processed = 0 ORDER BY published ASC"
        )
        return [_row_to_article(row) for row in cur.fetchall()]

    def get_articles_in_range(
        self, date_from: datetime, date_to: datetime
    ) -> list[Article]:
        """published が [date_from, date_to] の範囲の処理済み・要約あり記事を返す。"""
        cur = self._conn.execute(
            """
            SELECT * FROM articles
            WHERE is_processed = 1
              AND summary != ''
              AND published >= ?
              AND published <= ?
            ORDER BY published DESC
            """,
            (date_from.isoformat(), date_to.isoformat()),
        )
        return [_row_to_article(row) for row in cur.fetchall()]

    def get_summaries_in_range(
        self, date_from: datetime, date_to: datetime
    ) -> dict[str, str]:
        """get_articles_in_range と同範囲の {url: summary} dict を返す。"""
        cur = self._conn.execute(
            """
            SELECT url, summary FROM articles
            WHERE is_processed = 1
              AND summary != ''
              AND published >= ?
              AND published <= ?
            """,
            (date_from.isoformat(), date_to.isoformat()),
        )
        return {row["url"]: row["summary"] for row in cur.fetchall()}

    def get_all_processed(self) -> list[Article]:
        """is_processed=1 かつ summary が存在する全記事を published 降順で返す。"""
        cur = self._conn.execute(
            """
            SELECT * FROM articles
            WHERE is_processed = 1
              AND summary != ''
            ORDER BY published DESC
            """
        )
        return [_row_to_article(row) for row in cur.fetchall()]

    def get_all_summaries(self) -> dict[str, str]:
        """get_all_processed と同じ条件の {url: summary} dict を返す。"""
        cur = self._conn.execute(
            """
            SELECT url, summary FROM articles
            WHERE is_processed = 1
              AND summary != ''
            """
        )
        return {row["url"]: row["summary"] for row in cur.fetchall()}

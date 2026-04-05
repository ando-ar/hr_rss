"""renderer.py 変更時にサンプル HTML を再生成するスクリプト。

pre-commit フック（files: renderer.py）から呼び出される。
output/ 以下のプロファイル別 DB を読み込み、output/sample/sample.html を更新する。
DB が存在しない場合はスキップ（コミットは失敗しない）。
"""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
OUTPUT_DIR = ROOT / "output"
SAMPLE_PATH = ROOT / "output" / "sample" / "sample.html"
DAYS = 90


def main() -> int:
    from hr_rss.db import ArticleDB
    from hr_rss.renderer import ProfileResult, render_html_multi_profile

    db_paths = sorted(OUTPUT_DIR.glob("hr_rss_*.db"))
    if not db_paths:
        print("update_sample: DB が見つかりません。スキップします。", file=sys.stderr)
        return 0

    dt_to = datetime.now(UTC)
    dt_from = dt_to - timedelta(days=DAYS)

    profile_results: list[ProfileResult] = []
    for db_path in db_paths:
        profile_name = db_path.stem.removeprefix("hr_rss_")
        db = ArticleDB(db_path)
        articles = db.get_articles_in_range(dt_from, dt_to)
        summaries = db.get_summaries_in_range(dt_from, dt_to)
        db.close()
        if articles:
            profile_results.append(
                ProfileResult(name=profile_name, articles=articles, summaries=summaries)
            )

    if not profile_results:
        print("update_sample: 対象記事が 0 件です。スキップします。", file=sys.stderr)
        return 0

    html = render_html_multi_profile(profile_results, days=DAYS)
    SAMPLE_PATH.write_text(html, encoding="utf-8")
    print(
        f"update_sample: {SAMPLE_PATH.relative_to(ROOT)} を更新しました。",
        file=sys.stderr,
    )

    subprocess.run(["git", "add", str(SAMPLE_PATH)], check=True)  # noqa: S603 S607
    return 0


if __name__ == "__main__":
    sys.exit(main())

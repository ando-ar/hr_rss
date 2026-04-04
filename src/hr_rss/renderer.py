from datetime import datetime, timezone

from hr_rss.fetcher import Article


def render_markdown(articles: list[Article], summaries: dict[str, str], days: int) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines: list[str] = [
        f"# HR Tech 技術記事まとめ（過去 {days} 日間）",
        f"生成日: {now}",
        "",
    ]

    if not articles:
        lines.append("_該当記事なし_")
        return "\n".join(lines)

    for article in articles:
        lines.append(f"## [{article.title}]({article.url})")
        meta = f"**ソース**: {article.source}　**公開日**: {article.published.strftime('%Y-%m-%d')}"
        if article.labels:
            label_str = "　".join(f"`{lb}`" for lb in article.labels)
            meta += f"　**ラベル**: {label_str}"
        lines.append(meta)
        lines.append("")
        summary = summaries.get(article.url, "")
        if summary:
            lines.append(summary)
        else:
            lines.append("_(要約なし)_")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)

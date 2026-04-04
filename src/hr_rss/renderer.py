import html as _html
from datetime import UTC, datetime

from hr_rss.fetcher import Article

_LABEL_COLORS: dict[str, tuple[str, str]] = {
    "生成AI": ("#fce4ec", "#880e4f"),
    "機械学習": ("#e8f5e9", "#1b5e20"),
    "データサイエンス": ("#e3f2fd", "#0d47a1"),
    "自然言語処理": ("#f3e5f5", "#4a148c"),
    "推薦システム": ("#fff3e0", "#e65100"),
    "検索": ("#e0f7fa", "#006064"),
    "MLOps": ("#fafafa", "#212121"),
    "データエンジニアリング": ("#e8eaf6", "#1a237e"),
    "インフラ": ("#fbe9e7", "#bf360c"),
    "バックエンド": ("#f9fbe7", "#33691e"),
    "論文紹介": ("#ede7f6", "#311b92"),
    "アーキテクチャ": ("#e0f2f1", "#004d40"),
}
_DEFAULT_LABEL_COLORS = ("#eeeeee", "#333333")


def _chip_html(label: str) -> str:
    bg, fg = _LABEL_COLORS.get(label, _DEFAULT_LABEL_COLORS)
    style = (
        f"background:{bg};color:{fg};"
        "padding:3px 11px;border-radius:999px;font-size:0.76rem;"
        "font-weight:600;white-space:nowrap;display:inline-block;margin:2px 4px 2px 0"
    )
    return f'<span style="{style}">{_html.escape(label)}</span>'


def render_markdown(
    articles: list[Article], summaries: dict[str, str], days: int
) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d")
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
        date_str = article.published.strftime("%Y-%m-%d")
        meta = f"**ソース**: {article.source}　**公開日**: {date_str}"
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


def render_html(articles: list[Article], summaries: dict[str, str], days: int) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d")

    css = """
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: "Hiragino Kaku Gothic ProN", "Noto Sans JP", "Meiryo", sans-serif;
        background: #f0f2f8;
        color: #1a1d2e;
        line-height: 1.75;
        font-size: 16px;
    }
    header {
        background: #1a1d2e;
        color: #fff;
        padding: 28px 24px 20px;
    }
    .header-inner { max-width: 860px; margin: 0 auto; }
    header h1 { font-size: 1.45rem; font-weight: 700; letter-spacing: 0.02em; }
    .header-meta {
        margin-top: 6px;
        font-size: 0.88rem;
        color: #aab0c8;
    }
    .filter-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 16px;
    }
    .filter-btn {
        border: none;
        cursor: pointer;
        padding: 4px 14px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        background: rgba(255,255,255,0.12);
        color: #e0e4f0;
        transition: background 0.15s, color 0.15s;
        font-family: inherit;
    }
    .filter-btn:hover { background: rgba(255,255,255,0.22); }
    .filter-btn.active { background: #fff; color: #1a1d2e; }
    main {
        max-width: 860px;
        margin: 28px auto;
        padding: 0 16px;
    }
    .card {
        background: #fff;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        padding: 22px 24px;
        margin-bottom: 16px;
    }
    .card-title {
        font-size: 1.05rem;
        font-weight: 700;
        line-height: 1.5;
        margin-bottom: 8px;
    }
    .card-title a {
        color: #2563eb;
        text-decoration: none;
    }
    .card-title a:hover { text-decoration: underline; }
    .card-chips { margin-bottom: 10px; }
    .card-meta {
        font-size: 0.82rem;
        color: #7a7f99;
        margin-bottom: 12px;
    }
    .card-summary {
        font-size: 0.93rem;
        color: #3a3f55;
        line-height: 1.8;
    }
    .no-articles {
        text-align: center;
        color: #7a7f99;
        padding: 60px 0;
        font-size: 1rem;
    }
    footer {
        text-align: center;
        font-size: 0.78rem;
        color: #aab0c8;
        padding: 24px 0 36px;
    }
    """

    js = """
    (function(){
      var buttons = document.querySelectorAll('.filter-btn');
      var cards = document.querySelectorAll('.card');
      buttons.forEach(function(btn){
        btn.addEventListener('click', function(){
          buttons.forEach(function(b){ b.classList.remove('active'); });
          btn.classList.add('active');
          var label = btn.dataset.label;
          cards.forEach(function(card){
            if(label === 'all'){
              card.style.display = '';
            } else {
              var labels = card.dataset.labels ? card.dataset.labels.split('\\t') : [];
              card.style.display = labels.indexOf(label) >= 0 ? '' : 'none';
            }
          });
        });
      });
      if(buttons.length) buttons[0].classList.add('active');
    })();
    """

    # フィルターボタン：実際に登場するラベルのみ、_LABEL_COLORSの順序を維持
    all_labels_in_order = list(_LABEL_COLORS.keys())
    present_labels = [
        lb for lb in all_labels_in_order if any(lb in a.labels for a in articles)
    ]

    filter_btns = ['<button class="filter-btn" data-label="all">すべて</button>']
    for lb in present_labels:
        esc = _html.escape(lb)
        filter_btns.append(
            f'<button class="filter-btn" data-label="{esc}">{esc}</button>'
        )
    filter_bar_html = "\n        ".join(filter_btns)

    # 記事カード
    if not articles:
        cards_html = '<p class="no-articles">該当記事なし</p>'
    else:
        card_parts: list[str] = []
        for article in articles:
            data_labels = "\t".join(article.labels)
            chips = "".join(_chip_html(lb) for lb in article.labels)
            chips_div = f'<div class="card-chips">{chips}</div>' if chips else ""
            summary = summaries.get(article.url, "")
            summary_text = (
                _html.escape(summary)
                if summary
                else '<span style="color:#aab0c8">_(要約なし)_</span>'
            )
            url_esc = _html.escape(article.url)
            title_esc = _html.escape(article.title)
            src_esc = _html.escape(article.source)
            pub_date = article.published.strftime("%Y-%m-%d")
            dl_esc = _html.escape(data_labels)
            card_parts.append(
                f'    <article class="card" data-labels="{dl_esc}">\n'
                f'      <div class="card-title">'
                f'<a href="{url_esc}" target="_blank" rel="noopener">'
                f"{title_esc}</a></div>\n"
                f"      {chips_div}\n"
                f'      <p class="card-meta">'
                f"ソース: {src_esc}&emsp;公開日: {pub_date}</p>\n"
                f'      <p class="card-summary">{summary_text}</p>\n'
                f"    </article>"
            )
        cards_html = "\n".join(card_parts)

    count = len(articles)
    return (
        f"<!DOCTYPE html>\n"
        f'<html lang="ja">\n'
        f"<head>\n"
        f'  <meta charset="utf-8">\n'
        f'  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"  <title>HR Tech 技術記事まとめ（過去 {days} 日間）</title>\n"
        f"  <style>{css}</style>\n"
        f"</head>\n"
        f"<body>\n"
        f"  <header>\n"
        f'    <div class="header-inner">\n'
        f"      <h1>HR Tech 技術記事まとめ</h1>\n"
        f'      <p class="header-meta">'
        f"生成日: {now}&emsp;|&emsp;過去 {days} 日間&emsp;|&emsp;{count} 件</p>\n"
        f'      <div class="filter-bar">\n'
        f"        {filter_bar_html}\n"
        f"      </div>\n"
        f"    </div>\n"
        f"  </header>\n"
        f"  <main>\n"
        f"{cards_html}\n"
        f"  </main>\n"
        f"  <footer>HR RSS &mdash; Generated {now}</footer>\n"
        f"  <script>{js}</script>\n"
        f"</body>\n"
        f"</html>"
    )

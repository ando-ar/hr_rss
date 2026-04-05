import hashlib
import html as _html
import json
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


def _label_colors(label: str) -> tuple[str, str]:
    """ラベル名から背景色・文字色を返す。未知ラベルはハッシュで色を自動生成する。"""
    if label in _LABEL_COLORS:
        return _LABEL_COLORS[label]
    digest = hashlib.md5(label.encode(), usedforsecurity=False).digest()
    hue = int.from_bytes(digest[:2], "big") % 360
    bg = f"hsl({hue},60%,92%)"
    fg = f"hsl({hue},55%,28%)"
    return bg, fg


def _chip_html(label: str) -> str:
    bg, fg = _label_colors(label)
    style = (
        f"background:{bg};color:{fg};"
        "padding:3px 11px;border-radius:999px;font-size:0.76rem;"
        "font-weight:600;white-space:nowrap;display:inline-block;margin:2px 4px 2px 0"
    )
    return f'<span style="{style}">{_html.escape(label)}</span>'


def render_markdown(
    articles: list[Article],
    summaries: dict[str, str],
    days: int | None = None,
    *,
    label: str | None = None,
) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d")
    header_label = label if label else f"過去 {days} 日間"
    lines: list[str] = [
        f"# HR Tech 技術記事まとめ（{header_label}）",
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


def render_html(
    articles: list[Article],
    summaries: dict[str, str],
    days: int | None = None,
    *,
    label: str | None = None,
) -> str:
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
    .header-inner { max-width: 1100px; margin: 0 auto; }
    header h1 { font-size: 1.45rem; font-weight: 700; letter-spacing: 0.02em; }
    .header-meta {
        margin-top: 6px;
        font-size: 0.88rem;
        color: #aab0c8;
    }
    .layout {
        max-width: 1100px;
        margin: 0 auto;
        display: flex;
        gap: 24px;
        padding: 24px 16px;
        align-items: flex-start;
    }
    .sidebar {
        width: 200px;
        flex-shrink: 0;
        position: sticky;
        top: 24px;
        background: #fff;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        padding: 16px;
    }
    .sidebar-title {
        font-size: 0.82rem;
        font-weight: 700;
        color: #7a7f99;
        margin-bottom: 10px;
        letter-spacing: 0.05em;
    }
    .sidebar-clear {
        display: block;
        width: 100%;
        text-align: left;
        border: none;
        cursor: pointer;
        padding: 5px 8px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
        background: transparent;
        color: #7a7f99;
        font-family: inherit;
        margin-bottom: 8px;
        border-bottom: 1px solid #e8eaf0;
        padding-bottom: 10px;
    }
    .sidebar-clear:hover { color: #1a1d2e; }
    .label-checks { display: flex; flex-direction: column; gap: 4px; }
    .label-check {
        display: flex;
        align-items: center;
        gap: 7px;
        cursor: pointer;
        padding: 3px 4px;
        border-radius: 6px;
        transition: background 0.12s;
    }
    .label-check:hover { background: #f0f2f8; }
    .label-check input[type=checkbox] {
        width: 14px;
        height: 14px;
        flex-shrink: 0;
        cursor: pointer;
        accent-color: #2563eb;
    }
    .label-chip {
        padding: 2px 9px;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 600;
        white-space: nowrap;
    }
    .result-count {
        margin-top: 12px;
        font-size: 0.78rem;
        color: #aab0c8;
        border-top: 1px solid #e8eaf0;
        padding-top: 8px;
    }
    main {
        flex: 1;
        min-width: 0;
        padding-bottom: 36px;
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
      var checkboxes = document.querySelectorAll('.label-check input[type=checkbox]');
      var cards = document.querySelectorAll('.card');
      var clearBtn = document.getElementById('clear-all');
      var countEl = document.getElementById('result-count');

      function getSelected() {
        var sel = [];
        checkboxes.forEach(function(cb){ if(cb.checked) sel.push(cb.value); });
        return sel;
      }

      function updateCount() {
        var visible = 0;
        cards.forEach(function(c){ if(c.style.display !== 'none') visible++; });
        if(countEl) countEl.textContent = visible + '件表示 / 全' + cards.length + '件';
      }

      function applyFilter() {
        var selected = getSelected();
        cards.forEach(function(card){
          if(selected.length === 0){
            card.style.display = '';
          } else {
            var lbls = card.dataset.labels ? JSON.parse(card.dataset.labels) : [];
            var match = selected.every(function(s){ return lbls.indexOf(s) !== -1; });
            card.style.display = match ? '' : 'none';
          }
        });
        updateCount();
      }

      checkboxes.forEach(function(cb){
        cb.addEventListener('change', applyFilter);
      });

      if(clearBtn){
        clearBtn.addEventListener('click', function(){
          checkboxes.forEach(function(cb){ cb.checked = false; });
          applyFilter();
        });
      }

      updateCount();
    })();
    """

    # サイドバーボタン：実際に登場するラベルのみ
    # 既知ラベルは_LABEL_COLORSの定義順、未知ラベルはその後ろにアルファベット順で追加
    known_order = list(_LABEL_COLORS.keys())
    all_present: set[str] = {lb for a in articles for lb in a.labels}
    known_present = [lb for lb in known_order if lb in all_present]
    unknown_present = sorted(all_present - set(known_order))
    present_labels = known_present + unknown_present

    clear_btn = '<button class="sidebar-clear" id="clear-all">チェックをクリア</button>'
    check_items = []
    for lb in present_labels:
        esc = _html.escape(lb)
        bg, fg = _label_colors(lb)
        check_items.append(
            f'<label class="label-check">'
            f'<input type="checkbox" value="{esc}">'
            f'<span class="label-chip" style="background:{bg};color:{fg}">{esc}</span>'
            f"</label>"
        )
    checks_html = "\n        ".join(check_items)
    sidebar_html = (
        f"{clear_btn}\n"
        f'      <div class="label-checks">\n'
        f"        {checks_html}\n"
        f"      </div>"
    )

    # 記事カード
    if not articles:
        cards_html = '<p class="no-articles">該当記事なし</p>'
    else:
        card_parts: list[str] = []
        for article in articles:
            data_labels_json = json.dumps(article.labels, ensure_ascii=False)
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
            dl_esc = _html.escape(data_labels_json)
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

    header_label = label if label else f"過去 {days} 日間"
    count = len(articles)
    return (
        f"<!DOCTYPE html>\n"
        f'<html lang="ja">\n'
        f"<head>\n"
        f'  <meta charset="utf-8">\n'
        f'  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"  <title>HR Tech 技術記事まとめ（{header_label}）</title>\n"
        f"  <style>{css}</style>\n"
        f"</head>\n"
        f"<body>\n"
        f"  <header>\n"
        f'    <div class="header-inner">\n'
        f"      <h1>HR Tech 技術記事まとめ</h1>\n"
        f'      <p class="header-meta">'
        f"生成日: {now}&emsp;|&emsp;{header_label}&emsp;|&emsp;{count} 件</p>\n"
        f"    </div>\n"
        f"  </header>\n"
        f'  <div class="layout">\n'
        f'    <aside class="sidebar">\n'
        f'      <div class="sidebar-title">ラベルで絞り込む</div>\n'
        f"      {sidebar_html}\n"
        f'      <div class="result-count" id="result-count"></div>\n'
        f"    </aside>\n"
        f"    <main>\n"
        f"{cards_html}\n"
        f"    </main>\n"
        f"  </div>\n"
        f"  <footer>HR RSS &mdash; Generated {now}</footer>\n"
        f"  <script>{js}</script>\n"
        f"</body>\n"
        f"</html>"
    )

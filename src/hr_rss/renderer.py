import hashlib
import html as _html
import json
from datetime import UTC, datetime
from typing import NamedTuple

from hr_rss.fetcher import Article


class ProfileResult(NamedTuple):
    name: str
    articles: list[Article]
    summaries: dict[str, str]


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
        max-height: calc(100vh - 48px);
        overflow-y: auto;
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
    .month-select { display: flex; flex-direction: column; gap: 3px;
        margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #e8eaf0; }
    .month-radio { display: flex; align-items: center; gap: 7px; cursor: pointer;
        padding: 3px 4px; border-radius: 6px; font-size: 0.82rem;
        color: #3a3f55; transition: background 0.12s; }
    .month-radio:hover { background: #f0f2f8; }
    .month-radio input[type=radio] { width: 14px; height: 14px; flex-shrink: 0;
        cursor: pointer; accent-color: #2563eb; }
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
    .search-input {
        width: 100%; padding: 6px 10px; border: 1px solid #d0d4e8;
        border-radius: 7px; font-size: 0.83rem; font-family: inherit;
        margin-bottom: 12px; outline: none; color: #1a1d2e;
    }
    .search-input:focus { border-color: #2563eb; }
    .label-count {
        margin-left: auto; font-size: 0.72rem; color: #aab0c8; font-weight: 500;
    }
    .source-checks { display: flex; flex-direction: column; gap: 4px; }
    .source-check { display: flex; align-items: center; gap: 7px; cursor: pointer;
        padding: 3px 4px; border-radius: 6px; transition: background 0.12s; }
    .source-check:hover { background: #f0f2f8; }
    .source-check input[type=checkbox] { width: 14px; height: 14px; flex-shrink: 0;
        cursor: pointer; accent-color: #2563eb; }
    .source-name { font-size: 0.78rem; color: #3a3f55; white-space: nowrap;
        overflow: hidden; text-overflow: ellipsis; max-width: 118px; }
    """

    js = """
    (function(){
      var checkboxes = document.querySelectorAll('.label-check input[type=checkbox]');
      var sourceCheckboxes = document.querySelectorAll(
        '.source-check input[type=checkbox]');
      var cards = document.querySelectorAll('.card');
      var clearBtn = document.getElementById('clear-all');
      var countEl = document.getElementById('result-count');
      var searchInput = document.getElementById('search-input');
      var activeMonth = '';

      function getSelected() {
        var sel = [];
        checkboxes.forEach(function(cb){ if(cb.checked) sel.push(cb.value); });
        return sel;
      }

      function getSelectedSources() {
        var sel = [];
        sourceCheckboxes.forEach(function(cb){ if(cb.checked) sel.push(cb.value); });
        return sel;
      }

      function updateCount() {
        var visible = 0;
        cards.forEach(function(c){ if(c.style.display !== 'none') visible++; });
        if(countEl) countEl.textContent = visible + '件表示 / 全' + cards.length + '件';
      }

      function applyFilter() {
        var selected = getSelected();
        var selectedSources = getSelectedSources();
        var query = searchInput ? searchInput.value.trim().toLowerCase() : '';
        cards.forEach(function(card){
          var monthMatch = !activeMonth || card.dataset.month === activeMonth;
          var lbls = card.dataset.labels ? JSON.parse(card.dataset.labels) : [];
          var labelMatch = selected.length === 0 ||
            selected.every(function(s){ return lbls.indexOf(s) !== -1; });
          var sourceMatch = selectedSources.length === 0 ||
            selectedSources.indexOf(card.dataset.source) !== -1;
          var textMatch = !query ||
            (card.dataset.title || '').toLowerCase().indexOf(query) !== -1 ||
            (card.dataset.summary || '').toLowerCase().indexOf(query) !== -1;
          var show = monthMatch && labelMatch && sourceMatch && textMatch;
          card.style.display = show ? '' : 'none';
        });
        updateCount();
      }

      checkboxes.forEach(function(cb){
        cb.addEventListener('change', applyFilter);
      });

      sourceCheckboxes.forEach(function(cb){
        cb.addEventListener('change', applyFilter);
      });

      if(searchInput) searchInput.addEventListener('input', applyFilter);

      if(clearBtn){
        clearBtn.addEventListener('click', function(){
          checkboxes.forEach(function(cb){ cb.checked = false; });
          sourceCheckboxes.forEach(function(cb){ cb.checked = false; });
          if(searchInput) searchInput.value = '';
          applyFilter();
        });
      }

      document.querySelectorAll('input[name="month"]').forEach(function(radio){
        radio.addEventListener('change', function(){
          activeMonth = this.value;
          applyFilter();
        });
      });

      updateCount();
    })();
    """

    # 月ボタン：記事から登場するYYYY-MMを降順で抽出
    months_seen: list[str] = []
    for a in articles:
        m = a.published.strftime("%Y-%m")
        if m not in months_seen:
            months_seen.append(m)
    month_btns = [
        '<label class="month-radio">'
        '<input type="radio" name="month" value="" checked> すべて</label>'
    ]
    for m in months_seen:
        label_m = m[:4] + "/" + m[5:]
        month_btns.append(
            f'<label class="month-radio">'
            f'<input type="radio" name="month" value="{m}"> {label_m}</label>'
        )
    month_html = (
        '<div class="sidebar-title">月で絞り込む</div>\n'
        '      <div class="month-select">\n'
        "        " + "\n        ".join(month_btns) + "\n"
        "      </div>"
    )

    # サイドバーボタン：実際に登場するラベルのみ
    # 既知ラベルは_LABEL_COLORSの定義順、未知ラベルはその後ろにアルファベット順で追加
    known_order = list(_LABEL_COLORS.keys())
    all_present: set[str] = {lb for a in articles for lb in a.labels}
    known_present = [lb for lb in known_order if lb in all_present]
    unknown_present = sorted(all_present - set(known_order))
    present_labels = known_present + unknown_present

    label_counts: dict[str, int] = {}
    for _a in articles:
        for _lb in _a.labels:
            label_counts[_lb] = label_counts.get(_lb, 0) + 1

    source_counts: dict[str, int] = {}
    for _a in articles:
        source_counts[_a.source] = source_counts.get(_a.source, 0) + 1
    sources_sorted = sorted(source_counts.items(), key=lambda x: -x[1])

    clear_btn = '<button class="sidebar-clear" id="clear-all">チェックをクリア</button>'
    check_items = []
    for lb in present_labels:
        esc = _html.escape(lb)
        bg, fg = _label_colors(lb)
        cnt = label_counts.get(lb, 0)
        check_items.append(
            f'<label class="label-check">'
            f'<input type="checkbox" value="{esc}">'
            f'<span class="label-chip" style="background:{bg};color:{fg}">{esc}</span>'
            f'<span class="label-count">{cnt}</span>'
            f"</label>"
        )
    checks_html = "\n        ".join(check_items)

    source_items = []
    for _src, _cnt in sources_sorted:
        _src_esc = _html.escape(_src)
        source_items.append(
            f'<label class="source-check">'
            f'<input type="checkbox" value="{_src_esc}">'
            f'<span class="source-name" title="{_src_esc}">{_src_esc}</span>'
            f'<span class="label-count">{_cnt}</span>'
            f"</label>"
        )
    sources_checks_html = "\n        ".join(source_items)

    sidebar_html = (
        f'<input type="search" id="search-input" class="search-input"'
        f' placeholder="タイトル・要約を検索…">\n'
        f"      {month_html}\n"
        f"      {clear_btn}\n"
        f'      <div class="sidebar-title">ラベルで絞り込む</div>\n'
        f'      <div class="label-checks">\n'
        f"        {checks_html}\n"
        f"      </div>\n"
        f'      <div class="sidebar-title"'
        f' style="margin-top:12px">ソースで絞り込む</div>\n'
        f'      <div class="source-checks">\n'
        f"        {sources_checks_html}\n"
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
            sum_esc = _html.escape(summary)
            pub_date = article.published.strftime("%Y-%m-%d")
            pub_month = article.published.strftime("%Y-%m")
            dl_esc = _html.escape(data_labels_json)
            card_parts.append(
                f'    <article class="card" data-labels="{dl_esc}"'
                f' data-month="{pub_month}" data-source="{src_esc}"'
                f' data-title="{title_esc}" data-summary="{sum_esc}">\n'
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


def _build_cards_html(articles: list[Article], summaries: dict[str, str]) -> str:
    if not articles:
        return '<p class="no-articles">該当記事なし</p>'
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
        sum_esc = _html.escape(summary)
        pub_date = article.published.strftime("%Y-%m-%d")
        pub_month = article.published.strftime("%Y-%m")
        dl_esc = _html.escape(data_labels_json)
        card_parts.append(
            f'    <article class="card" data-labels="{dl_esc}"'
            f' data-month="{pub_month}" data-source="{src_esc}"'
            f' data-title="{title_esc}" data-summary="{sum_esc}">\n'
            f'      <div class="card-title">'
            f'<a href="{url_esc}" target="_blank" rel="noopener">'
            f"{title_esc}</a></div>\n"
            f"      {chips_div}\n"
            f'      <p class="card-meta">'
            f"ソース: {src_esc}&emsp;公開日: {pub_date}</p>\n"
            f'      <p class="card-summary">{summary_text}</p>\n'
            f"    </article>"
        )
    return "\n".join(card_parts)


def _build_sidebar_html(articles: list[Article], count_id: str) -> str:
    # 月ラジオボタン（name はパネルごとに固有）
    radio_name = f"month-{count_id}"
    months_seen: list[str] = []
    for a in articles:
        m = a.published.strftime("%Y-%m")
        if m not in months_seen:
            months_seen.append(m)
    month_btns = [
        f'<label class="month-radio">'
        f'<input type="radio" name="{radio_name}" value="" checked> すべて</label>'
    ]
    for m in months_seen:
        label_m = m[:4] + "/" + m[5:]
        month_btns.append(
            f'<label class="month-radio">'
            f'<input type="radio" name="{radio_name}" value="{m}"> {label_m}</label>'
        )
    month_html = (
        '<div class="sidebar-title">月で絞り込む</div>\n'
        '      <div class="month-select">\n'
        "        " + "\n        ".join(month_btns) + "\n"
        "      </div>"
    )

    known_order = list(_LABEL_COLORS.keys())
    all_present: set[str] = {lb for a in articles for lb in a.labels}
    known_present = [lb for lb in known_order if lb in all_present]
    unknown_present = sorted(all_present - set(known_order))
    present_labels = known_present + unknown_present

    label_counts: dict[str, int] = {}
    for _a in articles:
        for _lb in _a.labels:
            label_counts[_lb] = label_counts.get(_lb, 0) + 1

    source_counts: dict[str, int] = {}
    for _a in articles:
        source_counts[_a.source] = source_counts.get(_a.source, 0) + 1
    sources_sorted = sorted(source_counts.items(), key=lambda x: -x[1])

    clear_btn = '<button class="sidebar-clear panel-clear">チェックをクリア</button>'
    check_items = []
    for lb in present_labels:
        esc = _html.escape(lb)
        bg, fg = _label_colors(lb)
        cnt = label_counts.get(lb, 0)
        check_items.append(
            f'<label class="label-check">'
            f'<input type="checkbox" value="{esc}">'
            f'<span class="label-chip" style="background:{bg};color:{fg}">{esc}</span>'
            f'<span class="label-count">{cnt}</span>'
            f"</label>"
        )
    checks_html = "\n        ".join(check_items)

    source_items = []
    for _src, _cnt in sources_sorted:
        _src_esc = _html.escape(_src)
        source_items.append(
            f'<label class="source-check">'
            f'<input type="checkbox" value="{_src_esc}">'
            f'<span class="source-name" title="{_src_esc}">{_src_esc}</span>'
            f'<span class="label-count">{_cnt}</span>'
            f"</label>"
        )
    sources_checks_html = "\n        ".join(source_items)

    return (
        f'<input type="search" class="search-input"'
        f' placeholder="タイトル・要約を検索…">\n'
        f"      {month_html}\n"
        f"      {clear_btn}\n"
        f'      <div class="sidebar-title">ラベルで絞り込む</div>\n'
        f'      <div class="label-checks">\n'
        f"        {checks_html}\n"
        f"      </div>\n"
        f'      <div class="sidebar-title"'
        f' style="margin-top:12px">ソースで絞り込む</div>\n'
        f'      <div class="source-checks">\n'
        f"        {sources_checks_html}\n"
        f"      </div>\n"
        f'      <div class="result-count" id="{count_id}"></div>'
    )


def render_html_multi_profile(
    profile_results: list[ProfileResult],
    days: int | None = None,
    *,
    label: str | None = None,
) -> str:
    """複数プロファイルの記事をタブ付きで表示するHTMLを生成する。"""
    now = datetime.now(UTC).strftime("%Y-%m-%d")
    header_label = label if label else f"過去 {days} 日間"

    extra_css = """
    .profile-tabs {
        display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap;
    }
    .profile-tab {
        padding: 8px 18px; border-radius: 8px; border: none; cursor: pointer;
        font-size: 0.9rem; font-weight: 600; background: #e8eaf0; color: #7a7f99;
        font-family: inherit; transition: background 0.15s, color 0.15s;
    }
    .profile-tab.active { background: #2563eb; color: #fff; }
    .profile-tab:hover:not(.active) { background: #d4d8e8; }
    .profile-panel { display: none; }
    .profile-panel.active { display: flex; gap: 24px; align-items: flex-start; }
    .profile-panel .sidebar { width: 200px; flex-shrink: 0; position: sticky;
        top: 24px; max-height: calc(100vh - 48px); overflow-y: auto;
        background: #fff; border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07); padding: 16px; }
    .profile-panel main { flex: 1; min-width: 0; padding-bottom: 36px; }
    """

    # 単一プロファイル用のCSSは共有する（body, card, sidebar-title などは変わらず使う）
    base_css = """
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
        font-family: "Hiragino Kaku Gothic ProN", "Noto Sans JP", "Meiryo", sans-serif;
        background: #f0f2f8; color: #1a1d2e; line-height: 1.75; font-size: 16px;
    }
    header { background: #1a1d2e; color: #fff; padding: 28px 24px 20px; }
    .header-inner { max-width: 1100px; margin: 0 auto; }
    header h1 { font-size: 1.45rem; font-weight: 700; letter-spacing: 0.02em; }
    .header-meta { margin-top: 6px; font-size: 0.88rem; color: #aab0c8; }
    .layout { max-width: 1100px; margin: 0 auto; padding: 24px 16px; }
    .sidebar-title { font-size: 0.82rem; font-weight: 700; color: #7a7f99;
        margin-bottom: 10px; letter-spacing: 0.05em; }
    .sidebar-clear {
        display: block; width: 100%; text-align: left; border: none; cursor: pointer;
        padding: 5px 8px; border-radius: 6px; font-size: 0.8rem; font-weight: 600;
        background: transparent; color: #7a7f99; font-family: inherit;
        margin-bottom: 8px; border-bottom: 1px solid #e8eaf0; padding-bottom: 10px;
    }
    .sidebar-clear:hover { color: #1a1d2e; }
    .month-select { display: flex; flex-direction: column; gap: 3px;
        margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #e8eaf0; }
    .month-radio { display: flex; align-items: center; gap: 7px; cursor: pointer;
        padding: 3px 4px; border-radius: 6px; font-size: 0.82rem;
        color: #3a3f55; transition: background 0.12s; }
    .month-radio:hover { background: #f0f2f8; }
    .month-radio input[type=radio] { width: 14px; height: 14px; flex-shrink: 0;
        cursor: pointer; accent-color: #2563eb; }
    .label-checks { display: flex; flex-direction: column; gap: 4px; }
    .label-check { display: flex; align-items: center; gap: 7px; cursor: pointer;
        padding: 3px 4px; border-radius: 6px; transition: background 0.12s; }
    .label-check:hover { background: #f0f2f8; }
    .label-check input[type=checkbox] { width: 14px; height: 14px; flex-shrink: 0;
        cursor: pointer; accent-color: #2563eb; }
    .label-chip { padding: 2px 9px; border-radius: 999px; font-size: 0.76rem;
        font-weight: 600; white-space: nowrap; }
    .result-count { margin-top: 12px; font-size: 0.78rem; color: #aab0c8;
        border-top: 1px solid #e8eaf0; padding-top: 8px; }
    .card { background: #fff; border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07); padding: 22px 24px;
        margin-bottom: 16px; }
    .card-title { font-size: 1.05rem; font-weight: 700;
        line-height: 1.5; margin-bottom: 8px; }
    .card-title a { color: #2563eb; text-decoration: none; }
    .card-title a:hover { text-decoration: underline; }
    .card-chips { margin-bottom: 10px; }
    .card-meta { font-size: 0.82rem; color: #7a7f99; margin-bottom: 12px; }
    .card-summary { font-size: 0.93rem; color: #3a3f55; line-height: 1.8; }
    .no-articles { text-align: center; color: #7a7f99;
        padding: 60px 0; font-size: 1rem; }
    footer { text-align: center; font-size: 0.78rem;
        color: #aab0c8; padding: 24px 0 36px; }
    .search-input { width: 100%; padding: 6px 10px; border: 1px solid #d0d4e8;
        border-radius: 7px; font-size: 0.83rem; font-family: inherit;
        margin-bottom: 12px; outline: none; color: #1a1d2e; }
    .search-input:focus { border-color: #2563eb; }
    .label-count { margin-left: auto; font-size: 0.72rem;
        color: #aab0c8; font-weight: 500; }
    .source-checks { display: flex; flex-direction: column; gap: 4px; }
    .source-check { display: flex; align-items: center; gap: 7px; cursor: pointer;
        padding: 3px 4px; border-radius: 6px; transition: background 0.12s; }
    .source-check:hover { background: #f0f2f8; }
    .source-check input[type=checkbox] { width: 14px; height: 14px; flex-shrink: 0;
        cursor: pointer; accent-color: #2563eb; }
    .source-name { font-size: 0.78rem; color: #3a3f55; white-space: nowrap;
        overflow: hidden; text-overflow: ellipsis; max-width: 118px; }
    """

    # タブバー
    tabs_html_parts = []
    for i, pr in enumerate(profile_results):
        active = " active" if i == 0 else ""
        name_esc = _html.escape(pr.name)
        tabs_html_parts.append(
            f'<button class="profile-tab{active}" data-profile="{name_esc}">'
            f"{name_esc}</button>"
        )
    tabs_html = "\n    ".join(tabs_html_parts)

    # パネルごとにサイドバー + カードを生成
    panels_html_parts = []
    for i, pr in enumerate(profile_results):
        active = " active" if i == 0 else ""
        name_esc = _html.escape(pr.name)
        count_id = f"result-count-{pr.name}"
        sidebar = _build_sidebar_html(pr.articles, count_id)
        cards = _build_cards_html(pr.articles, pr.summaries)
        panels_html_parts.append(
            f'  <div class="profile-panel{active}" data-profile="{name_esc}">\n'
            f'    <aside class="sidebar">\n'
            f"      {sidebar}\n"
            f"    </aside>\n"
            f"    <main>\n"
            f"{cards}\n"
            f"    </main>\n"
            f"  </div>"
        )
    panels_html = "\n".join(panels_html_parts)

    total_count = sum(len(pr.articles) for pr in profile_results)

    js = """
    (function(){
      function applyFilter(panel) {
        var checkboxes = panel.querySelectorAll(
          '.label-check input[type=checkbox]');
        var sourceCheckboxes = panel.querySelectorAll(
          '.source-check input[type=checkbox]');
        var cards = panel.querySelectorAll('.card');
        var countEl = panel.querySelector('.result-count');
        var activeMonthRadio = panel.querySelector(
          '.month-radio input[type=radio]:checked');
        var activeMonth = activeMonthRadio ? activeMonthRadio.value : '';
        var searchInput = panel.querySelector('.search-input');
        var query = searchInput ? searchInput.value.trim().toLowerCase() : '';
        var selected = [];
        checkboxes.forEach(function(cb){ if(cb.checked) selected.push(cb.value); });
        var selectedSources = [];
        sourceCheckboxes.forEach(function(cb){
          if(cb.checked) selectedSources.push(cb.value);
        });
        var visible = 0;
        cards.forEach(function(card){
          var monthMatch = !activeMonth || card.dataset.month === activeMonth;
          var lbls = card.dataset.labels ? JSON.parse(card.dataset.labels) : [];
          var labelMatch = selected.length === 0 ||
            selected.every(function(s){ return lbls.indexOf(s) !== -1; });
          var sourceMatch = selectedSources.length === 0 ||
            selectedSources.indexOf(card.dataset.source) !== -1;
          var textMatch = !query ||
            (card.dataset.title || '').toLowerCase().indexOf(query) !== -1 ||
            (card.dataset.summary || '').toLowerCase().indexOf(query) !== -1;
          var show = monthMatch && labelMatch && sourceMatch && textMatch;
          card.style.display = show ? '' : 'none';
          if(show) visible++;
        });
        if(countEl) countEl.textContent = visible + '件表示 / 全' + cards.length + '件';
      }

      document.querySelectorAll('.profile-panel').forEach(function(panel){
        panel.querySelectorAll('.label-check input[type=checkbox]')
          .forEach(function(cb){
          cb.addEventListener('change', function(){ applyFilter(panel); });
        });
        panel.querySelectorAll('.source-check input[type=checkbox]')
          .forEach(function(cb){
          cb.addEventListener('change', function(){ applyFilter(panel); });
        });
        var si = panel.querySelector('.search-input');
        if(si) si.addEventListener('input', function(){ applyFilter(panel); });
        var clearBtn = panel.querySelector('.panel-clear');
        if(clearBtn){
          clearBtn.addEventListener('click', function(){
            panel.querySelectorAll('.label-check input[type=checkbox]')
                 .forEach(function(cb){ cb.checked = false; });
            panel.querySelectorAll('.source-check input[type=checkbox]')
                 .forEach(function(cb){ cb.checked = false; });
            var si2 = panel.querySelector('.search-input');
            if(si2) si2.value = '';
            applyFilter(panel);
          });
        }
        panel.querySelectorAll('.month-radio input[type=radio]').forEach(
          function(radio){
          radio.addEventListener('change', function(){ applyFilter(panel); });
        });
        applyFilter(panel);
      });

      var tabs = document.querySelectorAll('.profile-tab');
      var panels = document.querySelectorAll('.profile-panel');
      tabs.forEach(function(tab){
        tab.addEventListener('click', function(){
          tabs.forEach(function(t){ t.classList.remove('active'); });
          panels.forEach(function(p){ p.classList.remove('active'); });
          tab.classList.add('active');
          document.querySelector(
            '.profile-panel[data-profile="' + tab.dataset.profile + '"]'
          ).classList.add('active');
        });
      });
    })();
    """

    return (
        f"<!DOCTYPE html>\n"
        f'<html lang="ja">\n'
        f"<head>\n"
        f'  <meta charset="utf-8">\n'
        f'  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"  <title>HR Tech 技術記事まとめ（{header_label}）</title>\n"
        f"  <style>{base_css}{extra_css}</style>\n"
        f"</head>\n"
        f"<body>\n"
        f"  <header>\n"
        f'    <div class="header-inner">\n'
        f"      <h1>HR Tech 技術記事まとめ</h1>\n"
        f'      <p class="header-meta">'
        f"生成日: {now}&emsp;|&emsp;{header_label}"
        f"&emsp;|&emsp;合計 {total_count} 件</p>\n"
        f"    </div>\n"
        f"  </header>\n"
        f'  <div class="layout">\n'
        f'    <div class="profile-tabs">\n'
        f"    {tabs_html}\n"
        f"    </div>\n"
        f"{panels_html}\n"
        f"  </div>\n"
        f"  <footer>HR RSS &mdash; Generated {now}</footer>\n"
        f"  <script>{js}</script>\n"
        f"</body>\n"
        f"</html>"
    )

# CLAUDE.md

このファイルは、このリポジトリで作業する Claude Code (claude.ai/code) へのガイダンスを提供します。

## プロジェクト概要

HR業界各社のテックブログ・GitHubリポジトリを巡回し、技術的に価値のある記事を抽出してMarkdown/HTMLにまとめるツール。

- **言語**: Python 3.13
- **環境管理**: uv
- **Linter / Formatter**: ruff
- **型チェッカー**: ty
- **テスト**: pytest
- **pre-commit**: ruff / ty / git-secrets / detect-secrets / pip-audit（`.pre-commit-config.yaml`）

## ディレクトリ構成

- `src/hr_rss/` — アプリケーションコード
- `config/` — 設定ファイル（`feeds.yaml`, `exclude_keywords.yaml`）
- `scripts/` — 運用補助スクリプト（`check_feeds.py` など）
- `tests/` — テストコード
- `docs/` — ドキュメント

## 主要モジュール

- `fetcher.py` — RSSフィード取得（`fetch_feed`）および GitHub Issues 取得（`fetch_github_issues`）
- `scraper.py` — 記事本文のHTMLスクレイピング
- `filter.py` — 除外キーワードによるフィルタリング
- `llm.py` — Anthropic APIを使った分類・要約・ラベリング
- `renderer.py` — Markdown/HTML出力生成
- `config.py` — 設定ファイル読み込み（`Config` クラス）

## feeds.yaml の feed タイプ

`config/feeds.yaml` の各エントリには `type` フィールドを指定できる（省略時は `rss`）。

```yaml
- url: https://example.com/feed       # type省略 → RSSとして処理
  name: Example Blog

- url: https://github.com/org/repo    # GitHub Issuesとして処理
  name: Org ML Round Table
  type: github_issues
```

## テストの規約

- `tests/conftest.py` に共通フィクスチャを定義する
- プロパティベーステストには `hypothesis` を使用する
  - Hypothesis プロファイル: `dev`（デフォルト, 200例）/ `ci`（50例）/ `fast`（20例）
  - CI では `--hypothesis-profile=ci` を指定する
- カバレッジレポートは `htmlcov/` に出力される（gitignore 対象）

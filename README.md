# HR RSS — HR tech 技術記事アグリゲーター

HR業界各社のテックブログ・GitHubリポジトリを巡回し、技術的に価値のある記事だけを抽出してMarkdown/HTMLにまとめるツール。AIが資金調達・提携などのノイズを除外し、各記事の要約を日本語で生成します。

---

## セットアップ

### 1. uv のインストール

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows（PowerShell）:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

インストール後、新しいターミナルを開いてください。

### 2. 依存ライブラリのインストール

```bash
uv sync
```

### 3. 初期設定

```bash
uv run hr-rss setup
```

対話形式で Anthropic API キーを入力し、`.env` ファイルを作成します。
設定ファイル（フィード・プロンプト等）はプロファイルとして `config/profiles/` に同梱済みです。

APIキーは [console.anthropic.com](https://console.anthropic.com) で発行できます。

---

## 実行

### Windows の場合

プロジェクトフォルダ内の `.bat` ファイルをダブルクリックするだけで実行できます。

| ファイル | 説明 |
|---|---|
| `run.bat` | 過去7日間の記事を収集 |
| `run_report.bat` | 指定期間の記事をDBから再出力 |

### コマンドラインの場合

#### `run` — 記事を収集してDBに蓄積

```bash
# 全プロファイルを実行（デフォルト）→ タブ切り替えHTMLを出力
uv run hr-rss run

# 過去14日分
uv run hr-rss run --days 14

# 特定のプロファイルのみ実行
uv run hr-rss run --profile hr_datascience
```

実行が完了すると `output/` ディレクトリにHTMLファイルが生成され、ブラウザが自動的に開きます。
収集した記事は `output/hr_rss_<profile>.db`（SQLite）に蓄積されます。同じURLの記事は重複してLLM処理されません。

**プロファイルについて**: `config/profiles/` 以下に複数のプロファイルを用意できます。デフォルトでは全プロファイルを並行実行し、タブで切り替えられる統合HTMLを出力します。

| オプション | デフォルト | 説明 |
|---|---|---|
| `--days N` | `7` | 過去N日間の記事を対象にする |
| `--profile NAME` | なし（全プロファイル実行） | 実行するプロファイル名 |
| `--all-profiles` | — | 全プロファイルを明示的に実行（デフォルト動作と同じ） |
| `--output PATH` | `output/output_YYYYMMDD_all.html` | 出力ファイルのパス |
| `--db PATH` | `output/hr_rss_<profile>.db` | DBファイルのパス |
| `--no-db` | `false` | DB永続化をスキップして従来通りに動作する |
| `--open / --no-open` | `ON` | 生成後にブラウザで自動オープン |

---

#### `report` — 過去記事をDBから出力

`run` で蓄積した記事を任意の日付範囲で再出力します。LLMを呼ばずに即時生成されます。

```bash
# 2026年3月の記事をまとめて出力
uv run hr-rss report --from 2026-03-01 --to 2026-03-31

# --to を省略すると今日まで
uv run hr-rss report --from 2026-04-01
```

| オプション | デフォルト | 説明 |
|---|---|---|
| `--from DATE` | 必須 | 開始日（YYYY-MM-DD形式） |
| `--to DATE` | 今日 | 終了日（YYYY-MM-DD形式） |
| `--output PATH` | `output/report_FROM_TO.md` | 出力ファイルのパス（`.html` も同時生成） |
| `--db PATH` | `output/hr_rss.db` | DBファイルのパス |
| `--open / --no-open` | `ON` | 生成後にブラウザで自動オープン |

---

## 出力サンプル

`run` コマンド（当日実行分）:
```markdown
# HR Tech 技術記事まとめ（過去 7 日間）
生成日: 2026-04-05

## [LLMを活用した採用スクリーニングの仕組み](https://tech.smarthr.jp/entry/...)
**ソース**: SmartHR Tech Blog　**公開日**: 2026-04-03　**ラベル**: `生成AI`

候補者の職務経歴書をLLMで構造化し、ポジションごとのスコアリングを自動化した事例。
fine-tuningなしでもプロンプト設計により十分な精度を達成している。
```

---

## 詳細ドキュメント

- [フィード・除外キーワードの設定](docs/configuration.md)
- [フィード疎通確認スクリプト](docs/check_feeds.md)

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
| `run.bat` | 最新記事を収集してDBに蓄積 |
| `run_report.bat` | 全プロファイル・全期間の記事をDBから再出力 |

### コマンドラインの場合

#### `run` — 記事を収集してDBに蓄積

```bash
# 全プロファイルを実行（デフォルト）→ タブ切り替えHTMLを出力
uv run hr-rss run

# 直近14日分のみ出力したい場合
uv run hr-rss run --days 14

# 特定のプロファイルのみ実行
uv run hr-rss run --profile hr_datascience
```

実行が完了すると `output/output.html` が生成されブラウザが自動的に開きます。
収集した記事は `output/hr_rss_<profile>.db`（SQLite）に蓄積されます。同じURLの記事は重複してLLM処理されません。

**プロファイルについて**: `config/profiles/` 以下に複数のプロファイルを用意できます。デフォルトでは全プロファイルを並行実行し、タブで切り替えられる統合HTMLを出力します。

| オプション | デフォルト | 説明 |
|---|---|---|
| `--days N` | なし（全期間） | 出力を直近N日間に絞る |
| `--profile NAME` | なし（全プロファイル実行） | 実行するプロファイル名 |
| `--all-profiles` | — | 全プロファイルを明示的に実行（デフォルト動作と同じ） |
| `--output PATH` | `output/output.html` | 出力ファイルのパス |
| `--db PATH` | `output/hr_rss_<profile>.db` | DBファイルのパス |
| `--no-db` | `false` | DB永続化をスキップして従来通りに動作する |
| `--open / --no-open` | `ON` | 生成後にブラウザで自動オープン |

---

#### `report` — 全プロファイルの記事をDBから出力

`run` で蓄積した全プロファイルのDBを読み込み、タブ付きHTMLを生成します。LLMを呼ばずに即時生成されます。
`output/hr_rss_*.db` を自動検出するため、引数なしで実行するだけで全期間・全プロファイルのレポートが得られます。

```bash
# 全期間・全プロファイルをまとめて出力（引数不要）
uv run hr-rss report

# 期間を絞る場合
uv run hr-rss report --from 2026-03-01 --to 2026-03-31
```

| オプション | デフォルト | 説明 |
|---|---|---|
| `--from DATE` | なし（全期間） | 開始日（YYYY-MM-DD形式） |
| `--to DATE` | 今日 | 終了日（YYYY-MM-DD形式、`--from` 指定時のみ有効） |
| `--output PATH` | `output/report.html` | 出力ファイルのパス |
| `--open / --no-open` | `ON` | 生成後にブラウザで自動オープン |

---

## 出力サンプル

`run` コマンド（当日実行分）:
```markdown
# HR Tech 技術記事まとめ（全期間）
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

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

### 3. Anthropic API キーの設定

1. [console.anthropic.com](https://console.anthropic.com) でAPIキーを発行
2. プロジェクトルートに `.env` ファイルを作成

```bash
# macOS / Linux
echo 'ANTHROPIC_API_KEY=sk-ant-ここにキーを貼り付け' > .env
```

---

## 実行

```bash
# 過去7日分の記事を収集（デフォルト）
uv run python -m hr_rss

# 過去14日分
uv run python -m hr_rss --days 14

# 出力ファイル名を指定
uv run python -m hr_rss --output report.md
```

実行が完了すると `output/` ディレクトリに `.md` と `.html` の2ファイルが生成されます。

### オプション

| オプション | デフォルト | 説明 |
|---|---|---|
| `--days N` | `7` | 過去N日間の記事を対象にする |
| `--output PATH` | `output/output_YYYYMMDD.md` | 出力ファイルのパス（`.html` も同時生成） |

---

## 出力サンプル

```markdown
# HR Tech 技術記事まとめ（過去 7 日間）
生成日: 2026-04-05

## [LLMを活用した採用スクリーニングの仕組み](https://tech.smarthr.jp/entry/...)
**ソース**: SmartHR Tech Blog　**公開日**: 2026-04-03

候補者の職務経歴書をLLMで構造化し、ポジションごとのスコアリングを自動化した事例。
fine-tuningなしでもプロンプト設計により十分な精度を達成している。
```

---

## 詳細ドキュメント

- [フィード・除外キーワードの設定](docs/configuration.md)
- [フィード疎通確認スクリプト](docs/check_feeds.md)

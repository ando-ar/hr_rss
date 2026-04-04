# HR RSS — HR tech 技術記事アグリゲーター

HR業界の競合各社のテックブログ・プレスリリースを巡回し、**技術的に価値のある記事だけ**を抽出してMarkdownにまとめるツールです。AIが「資金調達」「提携」「勉強会」などのノイズを除外し、各記事の要約を日本語で生成します。

---

## クイックスタート

### 1. 前提：uv のインストール

`uv` はPythonのパッケージ管理ツールです。ターミナルで以下を実行してください。

**macOS / Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows（PowerShell）:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

インストール後、新しいターミナルを開いてください。

---

### 2. リポジトリのセットアップ

```bash
# 依存ライブラリを一括インストール（初回のみ）
uv sync
```

---

### 3. Anthropic API キーの取得

1. [console.anthropic.com](https://console.anthropic.com) にアクセスしてアカウントを作成
2. 「API Keys」メニューから新しいキーを発行
3. 発行されたキー（`sk-ant-...` で始まる文字列）をコピー

---

### 4. API キーの設定

プロジェクトのルートに `.env` ファイルを作成し、以下の1行を書き込みます。

```bash
# macOS / Linux
echo 'ANTHROPIC_API_KEY=sk-ant-ここにキーを貼り付け' > .env

# Windows（PowerShell）
'ANTHROPIC_API_KEY=sk-ant-ここにキーを貼り付け' | Out-File -Encoding utf8 .env
```

---

### 5. 実行

```bash
# 過去7日分の記事を収集（デフォルト）
uv run python -m hr_rss --days 7

# 過去14日分
uv run python -m hr_rss --days 14

# 出力ファイル名を指定
uv run python -m hr_rss --days 7 --output report.md
```

実行が完了すると、`output_YYYYMMDD.md`（例: `output_20260404.md`）が生成されます。

---

## 出力サンプル

```markdown
# HR Tech 技術記事まとめ（過去 7 日間）
生成日: 2026-04-04

## [LLMを活用した採用スクリーニングの仕組み](https://tech.smarthr.jp/entry/...)
**ソース**: SmartHR Tech Blog　**公開日**: 2026-04-02

候補者の職務経歴書をLLMで構造化し、ポジションごとのスコアリングを自動化した事例。
fine-tuningなしでもプロンプト設計により十分な精度を達成している。
既存のATSとの連携にはWebhookを使用しており、導入コストを抑えた構成が参考になる。

---

## [AI-Powered Workforce Planning in Workday](https://workday.com/blog/...)
**ソース**: Workday Technology　**公開日**: 2026-04-01

...
```

---

## 巡回対象フィードの編集

`src/hr_rss/feeds.yaml` を編集することで、巡回するサイトを追加・削除できます。

```yaml
feeds:
  - url: https://tech.smarthr.jp/feed
    name: SmartHR Tech Blog

  - url: https://your-target-site.com/feed
    name: 追加したいブログ名
```

RSSフィードのURLは通常 `/feed`、`/rss`、`/atom.xml` などのパスで公開されています。

---

## 除外キーワードのカスタマイズ

`src/hr_rss/config.py` の `_EXCLUDE_KEYWORDS` リストを編集することで、フィルタリングルールを調整できます。

---

## オプション一覧

| オプション | デフォルト | 説明 |
|---|---|---|
| `--days N` | `7` | 過去N日間の記事を対象にする |
| `--output PATH` | `output_YYYYMMDD.md` | 出力ファイルのパス |
| `--help` | — | ヘルプを表示 |

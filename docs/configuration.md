# 設定ファイルのリファレンス

設定はプロファイル単位で管理されており、`config/profiles/<profile_name>/` ディレクトリに置かれます。

```
config/profiles/
├── hr_datascience/     # データサイエンティスト向け（エンジニアリング記事）
├── market_research/    # 市場動向リサーチャー向け（採用・雇用市場トレンド）
└── competitive_ai/     # 競合調査向け企画職（採用・マッチング系プロダクト動向）
```

デフォルト実行（`uv run hr-rss run`）では全プロファイルを並行実行し、タブ切り替えHTMLを出力します。

---

## プロファイルの実行

```bash
# 全プロファイルを実行（デフォルト）
uv run hr-rss run

# 特定のプロファイルのみ実行
uv run hr-rss run --profile hr_datascience
```

---

## 各設定ファイル

各プロファイルディレクトリに以下の4ファイルを置きます。ファイルが存在しない場合は `config/` 直下にフォールバックします。

---

### feeds.yaml — 巡回対象フィード

#### RSS / Atom フィード

```yaml
feeds:
  - url: https://tech.smarthr.jp/feed
    name: SmartHR Tech Blog
```

- `url`: RSSまたはAtomフィードのURL（`/feed`、`/rss`、`/atom.xml` など）
- `name`: 出力に表示されるソース名
- `type`: 省略時は `rss` として処理

#### GitHub Issues フィード

論文紹介・勉強会記録など、GitHubのIssuesをフィードとして収集できます。
GitHubのAtomフィード（`.atom`）が無効なリポジトリでもREST API経由で動作します。

```yaml
  - url: https://github.com/org/repo
    name: 組織名 ML Round Table
    type: github_issues
```

- `url`: GitHubリポジトリのURL（`https://github.com/{owner}/{repo}` 形式）
- `type: github_issues` を必ず指定する

> GitHub REST APIは認証なしで60 req/hの制限があります。フィードを多数追加する場合は`GITHUB_TOKEN`環境変数での認証を検討してください。

#### フィード追加前の疎通確認

新しいフィードを追加する前に、URLが正しく取得できるか確認することを推奨します。

```bash
uv run python scripts/check_feeds.py --profile <profile_name>
```

詳細は [check_feeds.md](check_feeds.md) を参照してください。

---

### exclude_keywords.yaml — 除外キーワード

タイトルにこれらのキーワードが含まれる記事はLLM分類の前に除外されます。

```yaml
exclude_keywords:
  - 資金調達
  - 業務提携
  - プレスリリース
```

プロファイルの目的に応じて除外対象を調整します。例えば競合調査プロファイルでは「資金調達」は重要なシグナルのため除外しません。

---

### labels.yaml — 分類ラベル

LLMが記事を分類する際に使うラベル一覧。プロファイルの目的に合わせて定義します。

```yaml
labels:
  - 生成AI
  - 推薦システム
  - MLOps
```

---

### prompts.yaml — LLMプロンプト

記事の分類・要約に使うプロンプトをプロファイル別に定義します。

```yaml
classify_system: |
  ...（分類判断の指示）...

summarize_system: |
  ...（要約・ラベリングの指示）...
```

`summarize_system` 内の `{labels_json}` はラベル一覧に自動置換されます。

---

## 環境変数（.env）

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `ANTHROPIC_API_KEY` | 必須 | Anthropic APIキー（`sk-ant-...`） |
| `ANTHROPIC_API_MODEL` | 任意 | 使用するモデル名（デフォルト: `claude-haiku-4-5-20251001`） |

# 設定ファイルのリファレンス

設定ファイルはすべて `config/` ディレクトリに置かれています。

---

## feeds.yaml — 巡回対象フィード

### RSS / Atom フィード

```yaml
feeds:
  - url: https://tech.smarthr.jp/feed
    name: SmartHR Tech Blog
```

- `url`: RSSまたはAtomフィードのURL（`/feed`、`/rss`、`/atom.xml` など）
- `name`: 出力に表示されるソース名
- `type`: 省略時は `rss` として処理

### GitHub Issues フィード

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

### フィード追加前の疎通確認

新しいフィードを追加する前に、URLが正しく取得できるか確認することを推奨します。

```bash
uv run python scripts/check_feeds.py
```

詳細は [check_feeds.md](check_feeds.md) を参照してください。

---

## exclude_keywords.yaml — 除外キーワード

タイトルにこれらのキーワードが含まれる記事はLLM分類の前に除外されます。

```yaml
exclude_keywords:
  - 資金調達
  - 業務提携
  - プレスリリース
```

除外対象を増やすことでLLMの呼び出し回数を減らしてコストを抑えられます。

---

## 環境変数（.env）

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `ANTHROPIC_API_KEY` | 必須 | Anthropic APIキー（`sk-ant-...`） |
| `ANTHROPIC_API_MODEL` | 任意 | 使用するモデル名（デフォルト: `claude-haiku-4-5-20251001`） |

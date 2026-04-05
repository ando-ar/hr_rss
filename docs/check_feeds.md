# check_feeds.py — フィード疎通確認スクリプト

LLM APIを呼ばずに、`config/feeds.yaml` に登録されている全フィードへのHTTPアクセスを確認するスクリプトです。

## 基本的な使い方

```bash
# 全フィードの結果を表示
uv run python scripts/check_feeds.py

# NG / bozo警告のみ表示（フィード数が多い場合に便利）
uv run python scripts/check_feeds.py --no-verbose
```

## オプション

| オプション | デフォルト | 説明 |
|---|---|---|
| `--timeout FLOAT` | `15.0` | 1フィードあたりのタイムアウト（秒） |
| `--workers INT` | `10` | 並列スレッド数 |
| `--verbose / --no-verbose` | verbose | 全結果表示 / NG・bozo警告のみ表示 |
| `--profile NAME` | なし | チェックするプロファイル名（`config/profiles/<name>/`） |

プロファイルを省略すると `config/feeds.yaml`（存在する場合）を読みます。プロファイルを使っている場合は必ず `--profile` を指定してください。

```bash
# hr_datascience プロファイルのフィードを確認
uv run python scripts/check_feeds.py --profile hr_datascience --no-verbose
```

## 出力の見方

```
[OK]  SmartHR Tech Blog  200  30 entries  546ms
[OK?] Recruit Tech Blog  200  0 entries  823ms  bozo: not well-formed (invalid token)
[NG]  Some Blog  404  219ms  HTTP 404

Checked 24 feeds: 21 OK, 1 NG, 2 bozo-warnings
```

| タグ | 意味 |
|------|------|
| `[OK]` | HTTP 200 かつ feedparser でパース成功 |
| `[OK?]` | HTTP 200 だが feedparser が `bozo=True`（XML不正） |
| `[NG]` | HTTP エラー・タイムアウト・接続失敗 |

**GitHub Issues フィード**（`type: github_issues`）の場合、`rate-limit remaining: N` も表示されます。GitHub REST API は認証なしで 60 req/h の制限があります。

## 終了コード

| コード | 意味 |
|--------|------|
| `0` | 全フィードが OK（bozo警告は含まない） |
| `1` | 1件以上 NG あり |

## フィードが NG だった場合の対処

| エラー | 原因と対処 |
|--------|-----------|
| `HTTP 404` | フィードURLが廃止・移転。新しいURLを探して `config/feeds.yaml` を更新するか、エントリを削除する |
| `HTTP 429` | レート制限。URLは正しい。時間をおいて再実行する |
| `HTTP 406` | コンテンツネゴシエーション失敗。GitHub Issues の場合は `type: github_issues` を指定する |
| `Timeout` | ネットワーク遅延またはサイト障害。`--timeout` を延ばして再試行するか、エントリを削除する |
| `bozo` | XMLが不正だがHTTPアクセスは成功。feedparser が記事を取得できない場合はURLを調査する |

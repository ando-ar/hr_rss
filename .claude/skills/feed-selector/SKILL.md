---
name: feed-selector
description: >
  feeds.yaml に追加するフィード候補を選定・検証し、対話的に追記するスキル。

  次のような依頼に使うこと:
  「フィードを追加したい」「新しいブログを登録したい」「フィード候補を調べて」
  「〇〇社のRSSを追加」「フィードを整理したい」「不要なフィードを削除したい」
---

# Feed Selector

feeds.yaml へのフィード追加・削除・整理を対話的に行うスキル。

---

## ワークフロー

### 1. ユーザーの意図を確認する

ユーザーの依頼を次の3パターンに分類する:

- **A. 候補を探したい** — 「〇〇業界のフィードを追加したい」など
- **B. 特定URLを追加したい** — URLやブログ名が明示されている
- **C. 既存フィードを整理したい** — 不要フィードの削除・カテゴリ整理

### 2. 既存フィードを読み込む

```
config/feeds.yaml が存在する場合はそちら、なければ config/feeds.sample.yaml を読む。
```

現在登録済みの URL 一覧を把握し、重複候補を除外するために使う。

### 3-A: 候補を探す場合

1. **WebSearch でフィード候補を調査する**
   - 検索クエリ例: `"site:github.com" OR "tech blog" "{会社名}" RSS feed`
   - HR Tech・日本企業の場合: `"{会社名} テックブログ RSS"`
   - 候補は最大10件まで収集する

2. **各候補のフィードURLを確定する**
   - ブログトップページから RSS/Atom の URL を特定する (`/feed`, `/rss`, `/index.xml` など)
   - GitHub リポジトリの場合は `type: github_issues` を使う

3. **疎通確認を行う**
   ```bash
   uv run python scripts/check_feeds.py --no-verbose
   ```
   既存フィードのチェックも兼ねて実行し、追加候補の URL が到達可能か確認する。
   個別確認が必要な場合は WebFetch で直接 URL を取得して確認する。

4. **候補を提示してユーザーに選んでもらう**

   次の形式で一覧表示する:
   ```
   # フィード候補

   | # | 名前 | URL | カテゴリ | 備考 |
   |---|------|-----|----------|------|
   | 1 | SmartHR Tech Blog | https://tech.smarthr.jp/feed | HR Japan | 疎通OK |
   | 2 | Visional Engineering | https://engineering.visional.inc/index.xml | HR Japan | 疎通OK |
   ...

   追加したい番号を入力してください（例: 1,3,5 または all）:
   ```

### 3-B: 特定URLを追加する場合

1. URL が RSS フィードか GitHub リポジトリかを判定する
2. WebFetch でアクセス可能か確認する
3. フィード名を提案する（ユーザーが変更可能）
4. `feeds.yaml` へ追記する

### 3-C: 整理する場合

1. 既存フィードを全表示する
2. `check_feeds.py` で疎通NGのフィードを特定する
3. 削除候補をユーザーに提示して確認を取る

---

## feeds.yaml への追記ルール

### フォーマット

```yaml
  - url: https://example.com/feed
    name: Example Tech Blog

  - url: https://github.com/org/repo
    name: Org ML Round Table
    type: github_issues
```

### カテゴリコメント

既存の構造に合わせてコメントでグループ化する:

- `# ---- 日本 ----` — 日本企業のテックブログ
- `# ---- グローバル ----` — 海外HR Tech企業
- `# ---- 推薦・検索・ML（グローバル大手）----` — ML/AI系
- `# ---- HR tech ニュース（技術寄り）----` — ニュースメディア

新しいカテゴリが必要な場合はユーザーと相談して決める。

### 追記手順

1. `config/feeds.yaml` が存在しない場合は `config/feeds.sample.yaml` をコピーしてから編集する
2. 適切なカテゴリの末尾に追記する
3. 追記後、`check_feeds.py` で疎通確認する:
   ```bash
   uv run python scripts/check_feeds.py --no-verbose
   ```

---

## 重複チェック

追加前に必ず既存 URL と照合する。ドメインが同じでパスが異なる場合も警告する:

```
警告: example.com のフィードはすでに登録されています（https://example.com/rss）
別のセクションのフィードとして追加しますか？
```

---

## 削除の確認

フィードを削除する場合は必ずユーザーに確認を取る:

```
以下のフィードを削除します:
  - Lever Blog (https://www.lever.co/blog/feed/) — HTTP 404

削除してよいですか？ [y/N]:
```

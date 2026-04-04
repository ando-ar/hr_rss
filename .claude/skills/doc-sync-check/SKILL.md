---
name: doc-sync-check
description: >
  コードベースを検索して、実装とドキュメントが乖離している箇所を一覧化し、
  ユーザーに差分を表示しながら対話的に修正するスキル。

  次のような依頼に使うこと:
  「ドキュメントと実装があっていない」「ドキュメントが古い」「コードと README がズレている」
  「実装とドキュメントを同期したい」「doc-sync」「/doc-sync-check」。
---

# Doc-Sync-Check: 実装とドキュメントの乖離検出・修正スキル

ドキュメント（README、CLAUDE.md、docstring、コメント等）と実際の実装の間に生じた
乖離を体系的に検出し、ユーザーと対話しながら修正する。

---

## フェーズ概要

1. **Scan** — コードベースを走査して乖離候補を収集する
2. **Report** — 乖離をカテゴリ別に一覧表示する
3. **Fix** — ユーザーの確認を取りながら修正する

---

## Phase 1: Scan — 乖離候補の収集

### 1-1. 調査対象ファイルの把握

まずプロジェクト構造を把握する:

```
Glob: **/*.py, **/*.md, **/*.yaml, **/*.toml, **/*.json
（node_modules, .venv, __pycache__, .git, mlruns, htmlcov は除外）
```

重点的に調査するドキュメント:
- `README.md` / `README.*.md`
- `CLAUDE.md`
- `docs/**/*.md`
- `experiments/**/reports/*.md`
- Python モジュールの docstring（`src/**/*.py`）

重点的に調査する実装:
- `src/**/*.py` — 公開 API、関数シグネチャ、クラス定義
- `pyproject.toml` — 依存ライブラリ、スクリプトエントリポイント、設定
- `dvc.yaml` — パイプラインステージ
- `experiments/**/conf/**/*.yaml` — Hydra 設定

### 1-2. 乖離パターンの検出

以下のカテゴリで乖離を探す:

#### カテゴリ A: API・シグネチャの乖離
- ドキュメントに記載されている関数名・引数が実装と異なる
- docstring のパラメータ記述と実際の引数リストが不一致
- 削除された関数・クラスがドキュメントに残っている

検出方法:
```python
# Grep で public 関数を抽出
pattern: "^def [a-z]|^class [A-Z]"
files: src/**/*.py

# docstring 中のパラメータ記述を抽出
pattern: ":param |Args:|Parameters:|Returns:|Raises:"
files: src/**/*.py
```

#### カテゴリ B: 依存ライブラリの乖離
- `pyproject.toml` の `[project.dependencies]` / `[dependency-groups]` に記載されているが
  README やドキュメントに記載がない（または逆）
- バージョン制約がドキュメントと異なる

検出方法:
```
Read: pyproject.toml の dependencies セクション
Grep: README.md 内のライブラリ名言及
```

#### カテゴリ C: コマンド・スクリプトの乖離
- README に記載されている実行コマンドが存在しない・変更されている
- `pyproject.toml` の `[project.scripts]` と README の「使い方」が不一致
- Makefile / justfile のターゲット名がドキュメントと異なる

検出方法:
```
Grep: README.md 内の "```bash" ブロック → コマンドを抽出
Read: pyproject.toml の [project.scripts] セクション
Glob: Makefile, justfile
```

#### カテゴリ D: ファイルパス・ディレクトリ構造の乖離
- ドキュメントに記載されているパスが実際に存在しない
- CLAUDE.md の「規約」に書かれたディレクトリが作成されていない

検出方法:
```
Grep: ドキュメント内の相対パス（例: `src/`, `data/`, `experiments/`）
Bash: ls で実際のディレクトリ構造を確認
```

#### カテゴリ E: 設定・パラメータの乖離
- Hydra 設定ファイルのキー名がドキュメントと異なる
- MLflow の experiment 名がコードとドキュメントで不一致
- 環境変数名がドキュメントと異なる

検出方法:
```
Grep: ドキュメント内の設定キー言及
Read: experiments/**/conf/**/*.yaml
Grep: os.environ, os.getenv, dotenv パターン
```

#### カテゴリ F: CLAUDE.md 規約と実際の実装の乖離
- CLAUDE.md に「〇〇を使う」と書いてあるが、実装では別の方法を使っている
- テストの規約（conftest.py、hypothesis プロファイル等）が未実装
- ログ設計の規約（loguru）が実装されていない

検出方法:
```
Read: CLAUDE.md の各規約セクション
Grep: 規約で指定されたライブラリ・パターンの使用状況
```

---

## Phase 2: Report — 乖離の一覧表示

収集した乖離候補を以下の形式でユーザーに表示する:

```
## ドキュメント・実装 乖離レポート
生成日時: YYYY-MM-DD

---

### カテゴリ A: API・シグネチャの乖離 (N件)

| # | ファイル | 行 | ドキュメントの記述 | 実際の実装 | 重要度 |
|---|---------|-----|-------------------|-----------|--------|
| 1 | README.md:42 | — | `preprocess(df, drop_na=True)` | 関数が存在しない | 🔴 高 |
| 2 | src/model.py:15 | 15 | docstring: `param epochs: int` | シグネチャ: `n_epochs: int` | 🟡 中 |

---

### カテゴリ B: 依存ライブラリの乖離 (N件)
...

---

### サマリー
- 🔴 高: N件（ユーザーを誤解させる恐れがある）
- 🟡 中: N件（軽微な不整合）
- 🟢 低: N件（スタイル・文言のズレ）
- ✅ 問題なし: Nカテゴリ
```

重要度の定義:
- 🔴 高: ユーザーが手順通りに動かしてもエラーになる / API が完全に間違っている
- 🟡 中: 誤解を招く可能性があるが動作自体は問題ない
- 🟢 低: 文言・スタイルのズレ、軽微な不整合

---

## Phase 3: Fix — 対話的な修正

乖離レポートを表示した後、ユーザーに修正方針を確認する:

```
以下の修正方針を選んでください:

1. 全件まとめて修正する（自動）
2. カテゴリごとに確認しながら修正する
3. 個別に選んで修正する（番号を指定）
4. 修正せず、レポートのみ確認する

> どれにしますか？
```

### 修正ルール

**原則: 「実装」を正とし、「ドキュメント」を更新する**

ただし以下の場合は逆（ドキュメントが正しく実装が間違っている）かどうかをユーザーに確認:
- 🔴 高 の乖離で、ドキュメントの方が明らかに意図的に書かれている場合
- 最近のコミット（`git log --oneline -5`）でドキュメントが更新されているが実装が追いついていない場合

### 修正の実施

各乖離について:

1. **変更前後を表示する**:
   ```
   --- README.md (変更前)
   +++ README.md (変更後)
   @@ -42,3 +42,3 @@
   -preprocess(df, drop_na=True)
   +preprocess(df, remove_nulls=True)
   ```

2. **ユーザーの承認を取る**（カテゴリごと一括 or 個別）

3. **Edit ツールで修正を適用する**

4. **修正後の確認**:
   - 修正したファイルを再 Read して意図通りか確認
   - 関連する他のドキュメントへの波及がないか確認

### 修正完了レポート

```
## 修正完了レポート

修正済み: N件
スキップ: N件
手動対応が必要: N件

### 手動対応が必要な項目
- [3] src/train.py の docstring — 実装の意図が不明確なため、ユーザー判断が必要
  → 該当箇所: src/train.py:87
```

---

## 注意事項

- **自動生成ファイル**（`mlruns/`, `htmlcov/`, `__pycache__/`）は対象外
- **ドキュメントコメント以外のコードコメント**（`# TODO`, `# FIXME`）は別スキルの対象
- **テストコード**（`tests/`）内のドキュメント乖離は検出するが、修正は TDD スキルと連携する
- git でコミット前に `uv run pre-commit run --all-files` を推奨する

---

## コマンドリファレンス

```bash
# 変更後の lint チェック（ドキュメントも含む）
uv run pre-commit run --all-files

# 変更差分の確認
git diff

# 変更をステージング
git add -p
```

---
name: tdd
description: >
  Pythonの機能実装・クラス作成・関数追加・リファクタリング・バグ修正を
  TDD（テスト駆動開発）のRed-Green-Refactorサイクルで進めるスキル。pytest + uv 環境専用。

  次のような依頼には必ずこのスキルを使うこと（明示されていなくても積極的に適用する）：
  「〇〇を実装して」「〇〇クラスを作って」「〇〇関数を追加して」「新機能を追加」
  「TDDで」「テストを先に」「テストファースト」「リファクタリング」「バグ修正」。

  実装コードを1行も書く前に失敗するテストを書くことを厳守する。
---

# TDD Development

**絶対ルール: 実装コードを書く前に、必ず失敗するテストを書く。例外なし。**

テストを後から書くと「すでに動くコードの検証」になり、TDDの本来の目的（仕様の明確化・設計の強制・リグレッション防止）が失われる。テストが先にあることで、インターフェースを使う側の視点で設計できる。

---

## Red-Green-Refactor サイクル

### 🔴 Phase 1: Red — 失敗するテストを書く

**目的**: 「何を作るか」を明確にする。実装より先に期待する振る舞いを宣言する。

1. **実装する振る舞いを1つ選ぶ** — 小さく具体的に。
   - ❌「ユーザー管理ができる」
   - ✅「有効なメールアドレスでUserを生成すると、emailプロパティが保存される」

2. **テストを書く** — まだ存在しない関数・クラスを呼び出してよい。

3. **テストを実行して失敗を確認する**:
   ```bash
   uv run pytest tests/test_<module>.py::<test_name> -v
   ```

4. **失敗の種類を確認する**:
   - `ImportError` / `AttributeError` → 正常なRed（実装がまだない）
   - `AssertionError` → 理想的なRed（実装はあるが期待値と違う）
   - テストを実行せずに次へ進まないこと。「たぶん失敗するはず」は確認の代わりにならない。

```python
# 例: tests/test_user.py
def test_create_user_stores_email():
    user = User(email="alice@example.com")
    assert user.email == "alice@example.com"
```

---

### 🟢 Phase 2: Green — テストを通す最小限の実装を書く

**目的**: テストを通すこと。綺麗さは後回し。

1. テストを通すための**最小限のコードだけ**書く。
2. ハードコーディングも許容 — `return "alice@example.com"` でもテストが通るならOK（次のテストが壊す）。
3. **テストを実行して成功を確認する**:
   ```bash
   uv run pytest tests/test_<module>.py::<test_name> -v
   ```
4. **既存テストが壊れていないことも確認する**:
   ```bash
   uv run pytest tests/ -v
   ```

```python
# 例: src/<package>/user.py
class User:
    def __init__(self, email: str) -> None:
        self.email = email
```

---

### 🔵 Phase 3: Refactor — Greenを保ちながら品質を上げる

**目的**: 動くコードをより良いコードにする。テストがセーフティネット。

リファクタリングの対象:
- 重複の除去（同じロジックが複数箇所にある）
- 命名の改善（意図が伝わる名前に）
- 責務の分離（1つの関数/クラスが複数のことをしていないか）
- 型ヒントの追加

リファクタリング後は**必ずテストを実行**して全件パスを確認する:
```bash
uv run pytest tests/ -v
```

テストが全部通ることを確認してから次のサイクルへ。

---

## テストの書き方

### AAAパターン（Arrange-Act-Assert）

```python
def test_<振る舞いを平易な言葉で>():
    # Arrange: 前提条件をセットアップ
    user = User(email="alice@example.com")

    # Act: テスト対象の操作を実行
    result = user.display_name()

    # Assert: 期待する結果を検証
    assert result == "alice"
```

### テスト名の規約

意図が一目でわかる名前をつける。テストが失敗したとき、コードを読まずに何が壊れたかわかるように。

- `test_add_returns_sum_of_two_positive_numbers`
- `test_divide_raises_zero_division_error_when_divisor_is_zero`
- `test_user_email_is_normalized_to_lowercase`

### 1テスト1アサーション

テストが失敗したとき、原因が一目でわかるように。複数の振る舞いを確認したい場合はテストを分割する。

---

## サイクルのペース配分

> 「不安なら小さく、自信があれば大きく、迷ったら小さく」

1サイクルで実装するのは**1つの振る舞いだけ**。欲張らない。
すべてのテストがGreenになったら、次の振る舞いのテストを書く（Redから再スタート）。

**サイクル完了のチェックリスト:**
- [ ] テストを書いた
- [ ] テストがRedであることを確認した
- [ ] 最小限の実装でGreenにした
- [ ] Refactorした（必要なら）
- [ ] 全テストがGreenであることを確認した

---

## 既存コードのリファクタリング（応用）

既存コードを安全にリファクタリングするには、まず現状の振る舞いをテストで固める:

1. **既存の振る舞いをテストで記述する**（これが現状のドキュメントになる）
2. テストがGreenであることを確認する
3. リファクタリングを実施する
4. テストが引き続きGreenであることを確認する

---

## コマンドリファレンス

```bash
# 特定のテスト1件だけ実行（サイクル中に多用する）
uv run pytest tests/test_<module>.py::<test_name> -v

# ファイル全体のテストを実行
uv run pytest tests/test_<module>.py -v

# 全テストを実行（RefactorフェーズとGreen確認に使う）
uv run pytest tests/ -v

# 失敗したテストだけ再実行
uv run pytest tests/ -v --lf

# 短いサマリーで確認
uv run pytest tests/ -q
```

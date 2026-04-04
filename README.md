# プロジェクト名

## セットアップ

### 前提条件

- [uv](https://docs.astral.sh/uv/) がインストール済みであること
- [git-secrets](https://github.com/awslabs/git-secrets) がインストール済みであること
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) がインストール済みであること（GCS 使用時）

```bash
# git-secrets のインストール（未導入の場合）
brew install git-secrets        # macOS
# または
sudo apt-get install git-secrets  # Ubuntu/Debian
```

### 手順

```bash
# 1. 依存関係のインストール
uv sync

# 2. pre-commit フックの登録
uv run pre-commit install

# 3. git-secrets のパターン登録
git secrets --install
git secrets --register-aws   # AWS キーパターンの追加（任意）

# 4. 環境変数の設定
cp .env.example .env
# .env を編集して GCS_BUCKET_NAME などを入力（.env は .gitignore 対象）

# 5. GCS 認証（ADC を使用）
gcloud auth application-default login

# 6. データの取得
uv run dvc pull
```

## 開発

```bash
# Lint / Format
uv run ruff check .
uv run ruff format .

# 型チェック
uv run ty check

# テスト
uv run pytest tests/

# MLflow UI
uv run mlflow ui

# DVC パイプライン実行
uv run dvc repro
```

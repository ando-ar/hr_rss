# CLAUDE.md

このファイルは、このリポジトリで作業する Claude Code (claude.ai/code) へのガイダンスを提供します。

## プロジェクト概要

汎用 Python プロジェクトテンプレート。

- **言語**: Python
- **環境管理**: uv
- **Linter / Formatter**: ruff
- **型チェッカー**: ty
- **テスト**: pytest
- **pre-commit**: ruff / ty / git-secrets / detect-secrets / pip-audit（`.pre-commit-config.yaml`）

## ディレクトリ構成

- `src/<package>/` — アプリケーションコード
- `tests/` — テストコード
- `docs/` — ドキュメント

## テストの規約

- `tests/conftest.py` に共通フィクスチャを定義する
- プロパティベーステストには `hypothesis` を使用する
  - Hypothesis プロファイル: `dev`（デフォルト, 200例）/ `ci`（50例）/ `fast`（20例）
  - CI では `--hypothesis-profile=ci` を指定する
- カバレッジレポートは `htmlcov/` に出力される（gitignore 対象）

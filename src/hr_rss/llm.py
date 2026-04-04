import json
import os

import anthropic
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

_MODEL = "claude-haiku-4-5-20251001"
_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

_LABELS: list[str] = [
    "生成AI",
    "機械学習",
    "データサイエンス",
    "自然言語処理",
    "推薦システム",
    "検索",
    "MLOps",
    "データエンジニアリング",
    "インフラ",
    "バックエンド",
    "論文紹介",
    "アーキテクチャ",
]

_CLASSIFY_SYSTEM = """\
あなたはHR tech業界の技術記事フィルタリングの専門家です。
与えられた記事のタイトルと概要を読み、その記事が「技術者が読む価値のある技術記事」かどうかを判断してください。

【通過させるもの】
- 新サービスや新機能の技術的な解説
- AI・機械学習・LLMを活用したHR系プロダクトの紹介
- システムアーキテクチャや実装に関する記事
- HR techの技術的なコンセプト・設計思想の記事

【除外するもの】
- 資金調達・IPO・上場
- 企業間の提携・買収・合併
- 勉強会・イベント・セミナーの告知
- 採用・求人情報
- 受賞・表彰のプレスリリース

「YES」または「NO」のみで答えてください。
"""

_SUMMARIZE_AND_LABEL_SYSTEM = f"""\
あなたはHR tech業界のエンジニア向けに技術記事を要約・分類するアシスタントです。
記事の内容を読み、以下のJSON形式で回答してください。

{{
  "summary": "3〜5文の日本語要約",
  "labels": ["ラベル1", "ラベル2"]
}}

【要約のポイント】
- 何の技術を使っているか
- どんな課題を解決しているか
- どんな新規性・工夫があるか

【ラベルの選択ルール】
以下のリストから該当するものを1〜3個選んでください。リスト外の値は使用禁止です。
{json.dumps(_LABELS, ensure_ascii=False)}

JSONのみを出力し、コードブロックや前置きは不要です。
"""


def classify_article(title: str, excerpt: str) -> bool:
    try:
        response = _client.messages.create(
            model=_MODEL,
            max_tokens=10,
            system=_CLASSIFY_SYSTEM,
            messages=[{"role": "user", "content": f"タイトル: {title}\n概要: {excerpt}"}],
        )
        answer = response.content[0].text.strip().upper()
        return answer.startswith("YES")
    except Exception as e:
        logger.warning(f"classify_article failed: {e}")
        return False


def _strip_code_block(text: str) -> str:
    """```json ... ``` や ``` ... ``` で囲まれたコードブロックを除去する"""
    if text.startswith("```"):
        lines = text.splitlines()
        # 最初の行（```json など）と最後の行（```）を除去
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        return "\n".join(inner).strip()
    return text


def summarize_and_label(title: str, full_text: str, url: str) -> tuple[str, list[str]]:
    truncated = full_text[:8000] if len(full_text) > 8000 else full_text
    try:
        response = _client.messages.create(
            model=_MODEL,
            max_tokens=600,
            system=_SUMMARIZE_AND_LABEL_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": f"タイトル: {title}\nURL: {url}\n\n本文:\n{truncated}",
                }
            ],
        )
        raw = _strip_code_block(response.content[0].text.strip())
        data = json.loads(raw)
        summary = data.get("summary", "")
        labels = [lb for lb in data.get("labels", []) if lb in _LABELS]
        return summary, labels
    except Exception as e:
        logger.warning(f"summarize_and_label failed for {url}: {e}")
        return "", []

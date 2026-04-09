import json
import os
from pathlib import Path
from typing import cast

import anthropic
import yaml
from anthropic.types import TextBlock
from dotenv import load_dotenv
from loguru import logger

from hr_rss.config import _find_config_dir, _resolve_config_file, _resolve_with_fallback

load_dotenv()

_MODEL = os.environ.get("ANTHROPIC_API_MODEL", "claude-haiku-4-5-20251001")
_MAX_CHARS = int(os.environ.get("LLM_MAX_CHARS", "8000"))
_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

_run_stats: dict[str, int] = {
    "classify_calls": 0,
    "classify_in": 0,
    "classify_out": 0,
    "summarize_calls": 0,
    "summarize_in": 0,
    "summarize_out": 0,
}


def get_model() -> str:
    """現在使用中のモデル名を返す。"""
    return _MODEL


def reset_stats() -> None:
    """実行開始時に呼び出してトークン集計をリセットする。"""
    for k in _run_stats:
        _run_stats[k] = 0


def get_stats() -> dict[str, int]:
    """現在の集計値のコピーを返す。"""
    return dict(_run_stats)


def _load_labels(config_dir: Path, base_dir: Path | None = None) -> list[str]:
    if base_dir is not None and base_dir != config_dir:
        path = _resolve_with_fallback(config_dir, base_dir, "labels.yaml")
    else:
        path = _resolve_config_file(config_dir, "labels.yaml")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("labels", [])


def _load_prompts(config_dir: Path, base_dir: Path | None = None) -> dict[str, str]:
    if base_dir is not None and base_dir != config_dir:
        path = _resolve_with_fallback(config_dir, base_dir, "prompts.yaml")
    else:
        path = _resolve_config_file(config_dir, "prompts.yaml")
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _build_systems(
    config_dir: Path | None = None, base_dir: Path | None = None
) -> tuple[str, str, list[str]]:
    d = config_dir if config_dir is not None else _find_config_dir()
    labels = _load_labels(d, base_dir)
    prompts = _load_prompts(d, base_dir)

    classify_system = prompts["classify_system"].strip()
    summarize_template = prompts["summarize_system"].strip()
    summarize_system = summarize_template.replace(
        "{labels_json}", json.dumps(labels, ensure_ascii=False)
    )
    return classify_system, summarize_system, labels


# 遅延初期化：パスをキーとしてプロファイルごとにキャッシュ
_systems: dict[Path, tuple[str, str, list[str]]] = {}


def _get_systems(
    config_dir: Path | None = None, base_dir: Path | None = None
) -> tuple[str, str, list[str]]:
    key = config_dir if config_dir is not None else _find_config_dir()
    if key not in _systems:
        _systems[key] = _build_systems(config_dir, base_dir)
    return _systems[key]


def reset_llm_cache() -> None:
    """プロファイル切替やテスト時にシステムプロンプトのキャッシュをクリアする。"""
    _systems.clear()


def classify_article(
    title: str,
    excerpt: str,
    config_dir: Path | None = None,
    base_dir: Path | None = None,
) -> bool:
    classify_system, _, _ = _get_systems(config_dir, base_dir)
    try:
        response = _client.messages.create(
            model=_MODEL,
            max_tokens=10,
            system=classify_system,
            messages=[
                {"role": "user", "content": f"タイトル: {title}\n概要: {excerpt}"}
            ],
        )
        _run_stats["classify_calls"] += 1
        _run_stats["classify_in"] += response.usage.input_tokens
        _run_stats["classify_out"] += response.usage.output_tokens
        answer = cast(TextBlock, response.content[0]).text.strip().upper()
        return answer.startswith("YES")
    except Exception as e:
        logger.warning(f"classify_article failed: {e}")
        return False


def _strip_code_block(text: str) -> str:
    """```json ... ``` や ``` ... ``` で囲まれたコードブロックを除去する"""
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        return "\n".join(inner).strip()
    return text


def summarize_and_label(
    title: str,
    full_text: str,
    url: str,
    config_dir: Path | None = None,
    base_dir: Path | None = None,
) -> tuple[str, list[str]]:
    _, summarize_system, labels_vocab = _get_systems(config_dir, base_dir)
    truncated = full_text[:_MAX_CHARS] if len(full_text) > _MAX_CHARS else full_text
    try:
        response = _client.messages.create(
            model=_MODEL,
            max_tokens=600,
            system=summarize_system,
            messages=[
                {
                    "role": "user",
                    "content": f"タイトル: {title}\nURL: {url}\n\n本文:\n{truncated}",
                }
            ],
        )
        _run_stats["summarize_calls"] += 1
        _run_stats["summarize_in"] += response.usage.input_tokens
        _run_stats["summarize_out"] += response.usage.output_tokens
        raw = _strip_code_block(cast(TextBlock, response.content[0]).text.strip())
        data = json.loads(raw)
        summary = data.get("summary", "")
        labels = [lb for lb in data.get("labels", []) if lb in labels_vocab]
        return summary, labels
    except Exception as e:
        logger.warning(f"summarize_and_label failed for {url}: {e}")
        return "", []

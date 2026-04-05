import json
import os
from pathlib import Path
from typing import cast

import anthropic
import yaml
from anthropic.types import TextBlock
from dotenv import load_dotenv
from loguru import logger

from hr_rss.config import _find_config_dir, _resolve_config_file

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


def _load_labels(config_dir: Path) -> list[str]:
    path = _resolve_config_file(config_dir, "labels.yaml")
    with path.open() as f:
        data = yaml.safe_load(f)
    return data.get("labels", [])


def _load_prompts(config_dir: Path) -> dict[str, str]:
    path = _resolve_config_file(config_dir, "prompts.yaml")
    with path.open() as f:
        return yaml.safe_load(f)


def _build_systems(config_dir: Path | None = None) -> tuple[str, str, list[str]]:
    d = config_dir if config_dir is not None else _find_config_dir()
    labels = _load_labels(d)
    prompts = _load_prompts(d)

    classify_system = prompts["classify_system"].strip()
    summarize_template = prompts["summarize_system"].strip()
    summarize_system = summarize_template.replace(
        "{labels_json}", json.dumps(labels, ensure_ascii=False)
    )
    return classify_system, summarize_system, labels


# 遅延初期化：最初の呼び出し時にのみ設定ファイルを読み込む
_systems: tuple[str, str, list[str]] | None = None


def _get_systems() -> tuple[str, str, list[str]]:
    global _systems
    if _systems is None:
        _systems = _build_systems()
    return _systems


def classify_article(title: str, excerpt: str) -> bool:
    classify_system, _, _ = _get_systems()
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


def summarize_and_label(title: str, full_text: str, url: str) -> tuple[str, list[str]]:
    _, summarize_system, labels_vocab = _get_systems()
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

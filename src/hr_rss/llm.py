import json
import os
from pathlib import Path

import anthropic
import yaml
from dotenv import load_dotenv
from loguru import logger

from hr_rss.config import _find_config_dir

load_dotenv()

_MODEL = os.environ.get("ANTHROPIC_API_MODEL", "claude-haiku-4-5-20251001")
_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def _load_labels(config_dir: Path) -> list[str]:
    path = config_dir / "labels.yaml"
    if not path.exists():
        raise FileNotFoundError(f"labels file not found: {path}")
    with path.open() as f:
        data = yaml.safe_load(f)
    return data.get("labels", [])


def _load_prompts(config_dir: Path) -> dict[str, str]:
    path = config_dir / "prompts.yaml"
    if not path.exists():
        raise FileNotFoundError(f"prompts file not found: {path}")
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


# モジュールロード時に一度だけ設定を読み込む
_CLASSIFY_SYSTEM, _SUMMARIZE_AND_LABEL_SYSTEM, _LABELS = _build_systems()


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

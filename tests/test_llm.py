import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hr_rss.llm import (
    _build_systems,
    _strip_code_block,
    classify_article,
    get_stats,
    reset_stats,
    summarize_and_label,
)


def _mock_claude_response(text: str, input_tokens: int = 100, output_tokens: int = 10):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=text)]
    mock_msg.usage.input_tokens = input_tokens
    mock_msg.usage.output_tokens = output_tokens
    return mock_msg


@pytest.fixture(autouse=True)
def clear_stats():
    """各テスト前後にトークン集計をリセットする。"""
    reset_stats()
    yield
    reset_stats()


def test_classify_article_returns_true_for_tech_article():
    with patch("hr_rss.llm._client") as mock_client:
        mock_client.messages.create.return_value = _mock_claude_response("YES")
        result = classify_article(
            title="LLMで採用スクリーニングを自動化した話",
            excerpt="機械学習モデルを使って候補者のスキルを評価するシステムを構築しました。",
        )
    assert result is True


def test_classify_article_returns_false_for_non_tech():
    with patch("hr_rss.llm._client") as mock_client:
        mock_client.messages.create.return_value = _mock_claude_response("NO")
        result = classify_article(
            title="A社がB社と資本提携",
            excerpt="両社は今後の事業拡大に向けて協力関係を強化します。",
        )
    assert result is False


def test_classify_article_returns_false_on_api_error():
    with patch("hr_rss.llm._client") as mock_client:
        mock_client.messages.create.side_effect = Exception("API error")
        result = classify_article(title="任意のタイトル", excerpt="任意の概要")
    assert result is False


def test_summarize_and_label_returns_summary_and_labels():
    payload = json.dumps(
        {"summary": "LLMで採用を効率化した事例。", "labels": ["生成AI", "機械学習"]}
    )
    with patch("hr_rss.llm._client") as mock_client:
        mock_client.messages.create.return_value = _mock_claude_response(payload)
        summary, labels = summarize_and_label(
            title="LLMで採用スクリーニング",
            full_text="長い本文テキスト...",
            url="https://example.com",
        )
    assert "LLM" in summary
    assert "生成AI" in labels
    assert "機械学習" in labels


def test_summarize_and_label_returns_empty_on_api_error():
    with patch("hr_rss.llm._client") as mock_client:
        mock_client.messages.create.side_effect = Exception("API error")
        summary, labels = summarize_and_label(
            title="タイトル", full_text="本文", url="https://example.com"
        )
    assert summary == ""
    assert labels == []


def test_summarize_and_label_returns_empty_on_invalid_json():
    with patch("hr_rss.llm._client") as mock_client:
        mock_client.messages.create.return_value = _mock_claude_response(
            "これはJSONではない"
        )
        summary, labels = summarize_and_label(
            title="タイトル", full_text="本文", url="https://example.com"
        )
    assert summary == ""
    assert labels == []


def test_summarize_and_label_filters_invalid_labels():
    """ラベルリストにない値はフィルタされること"""
    payload = json.dumps({"summary": "要約", "labels": ["生成AI", "存在しないラベル"]})
    with patch("hr_rss.llm._client") as mock_client:
        mock_client.messages.create.return_value = _mock_claude_response(payload)
        _, labels = summarize_and_label(
            title="タイトル", full_text="本文", url="https://example.com"
        )
    assert "生成AI" in labels
    assert "存在しないラベル" not in labels


def test_summarize_and_label_handles_json_in_code_block():
    """ClaudeがJSONをコードブロックで返した場合も正常にパースできること"""
    payload = '```json\n{"summary": "要約テキスト", "labels": ["生成AI"]}\n```'
    with patch("hr_rss.llm._client") as mock_client:
        mock_client.messages.create.return_value = _mock_claude_response(payload)
        summary, labels = summarize_and_label(
            title="タイトル", full_text="本文", url="https://example.com"
        )
    assert summary == "要約テキスト"
    assert labels == ["生成AI"]


def test_classify_article_empty_content_returns_false():
    """response.content が空リストのとき IndexError を捕捉して False を返すこと"""
    with patch("hr_rss.llm._client") as mock_client:
        mock_msg = MagicMock()
        mock_msg.content = []
        mock_client.messages.create.return_value = mock_msg
        result = classify_article(title="タイトル", excerpt="概要")
    assert result is False


def test_summarize_and_label_missing_summary_key():
    """JSON に summary キーがない場合は空文字列を返すこと"""
    payload = json.dumps({"labels": ["生成AI"]})
    with patch("hr_rss.llm._client") as mock_client:
        mock_client.messages.create.return_value = _mock_claude_response(payload)
        summary, labels = summarize_and_label(
            title="タイトル", full_text="本文", url="https://example.com"
        )
    assert summary == ""
    assert "生成AI" in labels


def test_summarize_and_label_labels_not_a_list():
    """JSON の labels が文字列など非リスト型のとき labels が空リストになること。
    summary は正常に取得される（文字列イテレーションで全要素が _LABELS 外になる）"""
    payload = json.dumps({"summary": "要約", "labels": "生成AI"})
    with patch("hr_rss.llm._client") as mock_client:
        mock_client.messages.create.return_value = _mock_claude_response(payload)
        summary, labels = summarize_and_label(
            title="タイトル", full_text="本文", url="https://example.com"
        )
    assert labels == []


def test_strip_code_block_no_closing_fence():
    """閉じ ``` がない場合でも先頭行（fence行）を除いた内容を返すこと"""
    text = '```json\n{"key": "value"}'
    result = _strip_code_block(text)
    assert result == '{"key": "value"}'


def test_strip_code_block_plain_fence():
    """json 指定なしの ``` フェンスも正しく除去すること"""
    text = '```\n{"key": "value"}\n```'
    result = _strip_code_block(text)
    assert result == '{"key": "value"}'


class TestRunStats:
    def test_classify_article_accumulates_stats(self):
        with patch("hr_rss.llm._client") as mock_client:
            mock_client.messages.create.return_value = _mock_claude_response(
                "YES", input_tokens=200, output_tokens=5
            )
            classify_article(title="タイトル", excerpt="概要")

        stats = get_stats()
        assert stats["classify_calls"] == 1
        assert stats["classify_in"] == 200
        assert stats["classify_out"] == 5
        assert stats["summarize_calls"] == 0

    def test_summarize_and_label_accumulates_stats(self):
        payload = json.dumps({"summary": "要約", "labels": ["生成AI"]})
        with patch("hr_rss.llm._client") as mock_client:
            mock_client.messages.create.return_value = _mock_claude_response(
                payload, input_tokens=500, output_tokens=80
            )
            summarize_and_label(
                title="タイトル", full_text="本文", url="https://example.com"
            )

        stats = get_stats()
        assert stats["summarize_calls"] == 1
        assert stats["summarize_in"] == 500
        assert stats["summarize_out"] == 80
        assert stats["classify_calls"] == 0

    def test_stats_accumulate_across_multiple_calls(self):
        with patch("hr_rss.llm._client") as mock_client:
            mock_client.messages.create.return_value = _mock_claude_response(
                "YES", input_tokens=100, output_tokens=5
            )
            classify_article(title="記事1", excerpt="概要1")
            classify_article(title="記事2", excerpt="概要2")

        stats = get_stats()
        assert stats["classify_calls"] == 2
        assert stats["classify_in"] == 200
        assert stats["classify_out"] == 10

    def test_api_error_does_not_increment_stats(self):
        with patch("hr_rss.llm._client") as mock_client:
            mock_client.messages.create.side_effect = Exception("API error")
            classify_article(title="タイトル", excerpt="概要")

        stats = get_stats()
        assert stats["classify_calls"] == 0
        assert stats["classify_in"] == 0

    def test_reset_stats_clears_all_counts(self):
        with patch("hr_rss.llm._client") as mock_client:
            mock_client.messages.create.return_value = _mock_claude_response("YES")
            classify_article(title="タイトル", excerpt="概要")

        reset_stats()
        stats = get_stats()
        assert all(v == 0 for v in stats.values())

    def test_get_stats_returns_copy(self):
        """get_stats() の戻り値を書き換えても内部状態に影響しないこと。"""
        stats = get_stats()
        stats["classify_calls"] = 999
        assert get_stats()["classify_calls"] == 0


class TestBuildSystems:
    def _write_config(
        self, tmp_path: Path, labels: list[str], classify_sys: str, summarize_sys: str
    ) -> None:
        (tmp_path / "labels.yaml").write_text(
            "labels:\n" + "".join(f"  - {lb}\n" for lb in labels),
            encoding="utf-8",
        )
        (tmp_path / "prompts.yaml").write_text(
            f"classify_system: '{classify_sys}'\nsummarize_system: '{summarize_sys}'\n",
            encoding="utf-8",
        )

    def test_returns_classify_system_and_labels(self, tmp_path):
        self._write_config(
            tmp_path, ["生成AI", "MLOps"], "Classify.", "Summarize {labels_json}."
        )
        classify_sys, _, labels = _build_systems(tmp_path)
        assert classify_sys == "Classify."
        assert "生成AI" in labels
        assert "MLOps" in labels

    def test_injects_labels_json_into_summarize_system(self, tmp_path):
        self._write_config(tmp_path, ["生成AI"], "C.", "Labels: {labels_json}")
        _, summarize_sys, _ = _build_systems(tmp_path)
        assert "生成AI" in summarize_sys

    def test_raises_if_labels_yaml_missing(self, tmp_path):
        (tmp_path / "prompts.yaml").write_text(
            "classify_system: 'x'\nsummarize_system: 'x'\n"
        )
        with pytest.raises(FileNotFoundError, match="labels"):
            _build_systems(tmp_path)

    def test_raises_if_prompts_yaml_missing(self, tmp_path):
        (tmp_path / "labels.yaml").write_text("labels:\n  - 生成AI\n")
        with pytest.raises(FileNotFoundError, match="prompts"):
            _build_systems(tmp_path)

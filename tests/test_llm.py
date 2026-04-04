import json
from unittest.mock import MagicMock, patch

from hr_rss.llm import _strip_code_block, classify_article, summarize_and_label


def _mock_claude_response(text: str):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=text)]
    return mock_msg


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

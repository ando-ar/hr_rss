import pytest

from hr_rss.filter import is_excluded


@pytest.mark.parametrize(
    "title",
    [
        "SmartHRが10億円の資金調達を実施",
        "〇〇社との業務提携について",
        "エンジニア勉強会を開催します",
        "Workday Raises $500M in Series D",
        "Company X Partners with Company Y",
        "We're Hiring Senior Engineers",
    ],
)
def test_is_excluded_returns_true_for_noise(title):
    keywords = ["資金調達", "提携", "勉強会", "raises", "partners with", "we're hiring"]
    assert is_excluded(title, keywords) is True


@pytest.mark.parametrize(
    "title",
    [
        "AIを活用した採用スクリーニングの仕組み",
        "LLMでスキルマッチングを実装した話",
        "Workday Introduces AI-Powered Workforce Planning",
        "How We Built Our New Recommendation Engine",
    ],
)
def test_is_excluded_returns_false_for_tech_articles(title):
    keywords = ["資金調達", "提携", "勉強会", "raises", "partners with", "we're hiring"]
    assert is_excluded(title, keywords) is False


def test_is_excluded_is_case_insensitive():
    assert is_excluded("Company RAISES $10M", ["raises"]) is True


def test_is_excluded_with_empty_keywords():
    assert is_excluded("任意のタイトル", []) is False

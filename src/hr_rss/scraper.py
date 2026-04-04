import httpx
from bs4 import BeautifulSoup
from loguru import logger

_TIMEOUT = 15.0
_HEADERS = {"User-Agent": "hr-rss-bot/1.0 (tech article aggregator)"}
_NOISE_TAGS = ["nav", "footer", "header", "aside", "script", "style", "noscript"]


def scrape_text(url: str) -> str:
    try:
        response = httpx.get(url, timeout=_TIMEOUT, headers=_HEADERS, follow_redirects=True)
        response.raise_for_status()
    except Exception as e:
        logger.warning(f"Failed to scrape {url}: {e}")
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()

    # <article> があればその中を、なければ <main>、なければ <body> を使う
    container = soup.find("article") or soup.find("main") or soup.find("body")
    if container is None:
        return ""

    return container.get_text(separator="\n", strip=True)

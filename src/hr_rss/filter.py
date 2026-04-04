def is_excluded(title: str, keywords: list[str]) -> bool:
    lower = title.lower()
    return any(kw.lower() in lower for kw in keywords)

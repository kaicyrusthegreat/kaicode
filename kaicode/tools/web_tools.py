"""Web fetch tool — retrieve and clean web page content."""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Any


_SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "noscript", "svg"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._lines: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self._lines.append(stripped)

    def get_text(self) -> str:
        return "\n".join(self._lines)


def web_fetch(url: str, max_chars: int = 6000) -> dict[str, Any]:
    """Fetch a URL and return its cleaned text content. Use for docs, APIs, and references."""
    try:
        max_chars = int(max_chars)
    except (ValueError, TypeError):
        max_chars = 6000

    try:
        import httpx
        resp = httpx.get(
            url, timeout=20, follow_redirects=True,
            headers={"User-Agent": "KaiCode/1.0 (developer assistant)"},
        )
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "html" in content_type:
            extractor = _TextExtractor()
            extractor.feed(resp.text)
            text = extractor.get_text()
        elif "json" in content_type:
            text = resp.text
        else:
            text = resp.text

        text = text[:max_chars]
        return {
            "url":     url,
            "content": text,
            "length":  len(text),
            "truncated": len(resp.text) > max_chars,
        }
    except Exception as e:
        return {"error": str(e), "url": url}

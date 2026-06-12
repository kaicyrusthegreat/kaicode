"""Web search tool — search the internet using DuckDuckGo (no API key needed)."""

from __future__ import annotations

import re
from typing import Any
from html.parser import HTMLParser


class _DDGResultParser(HTMLParser):
    """Parse DuckDuckGo HTML search results."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._in_result = False
        self._in_title = False
        self._in_snippet = False
        self._current: dict[str, str] = {}
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attr_dict = dict(attrs)
        cls = attr_dict.get("class", "")

        if tag == "a" and "result__a" in cls:
            self._in_title = True
            self._current = {"title": "", "url": attr_dict.get("href", ""), "snippet": ""}
        elif tag == "a" and "result__snippet" in cls:
            self._in_snippet = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_title:
            self._in_title = False
        elif tag == "a" and self._in_snippet:
            self._in_snippet = False
            if self._current.get("title"):
                self.results.append(self._current)
                self._current = {}

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._current["title"] = self._current.get("title", "") + data.strip()
        elif self._in_snippet:
            self._current["snippet"] = self._current.get("snippet", "") + data.strip()


def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the web using DuckDuckGo. Returns titles, URLs, and snippets."""
    try:
        max_results = int(max_results)
    except (ValueError, TypeError):
        max_results = 5

    try:
        import httpx

        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
            },
            timeout=15,
            follow_redirects=True,
        )
        resp.raise_for_status()

        parser = _DDGResultParser()
        parser.feed(resp.text)

        results = parser.results[:max_results]

        # Clean up URLs (DuckDuckGo wraps them)
        for r in results:
            url = r.get("url", "")
            # Extract actual URL from DDG redirect
            match = re.search(r"uddg=([^&]+)", url)
            if match:
                from urllib.parse import unquote

                r["url"] = unquote(match.group(1))

        if not results:
            # Fallback: try to extract from the raw HTML with regex
            titles = re.findall(r'class="result__a"[^>]*>([^<]+)<', resp.text)
            snippets = re.findall(r'class="result__snippet"[^>]*>([^<]+)<', resp.text)
            urls = re.findall(r'class="result__url"[^>]*>([^<]+)<', resp.text)
            for i in range(min(max_results, len(titles))):
                results.append(
                    {
                        "title": titles[i].strip() if i < len(titles) else "",
                        "snippet": snippets[i].strip() if i < len(snippets) else "",
                        "url": urls[i].strip() if i < len(urls) else "",
                    }
                )

        return {
            "query": query,
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        return {"error": str(e), "query": query}

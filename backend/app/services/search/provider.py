from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    source: str = "web"


class SearchProvider(ABC):
    name: str

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        ...


class DuckDuckGoSearchProvider(SearchProvider):
    name = "duckduckgo"

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            logger.error("duckduckgo-search not installed")
            return []

        results: list[SearchResult] = []
        try:
            # DDGS is sync; run in thread to avoid blocking
            import asyncio

            def _run() -> list[dict]:
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=max_results))

            raw = await asyncio.to_thread(_run)
            for item in raw:
                results.append(
                    SearchResult(
                        title=item.get("title") or "",
                        url=item.get("href") or item.get("link") or "",
                        snippet=item.get("body") or item.get("snippet") or "",
                        source=self.name,
                    )
                )
        except Exception:
            logger.exception("DuckDuckGo search failed for query=%s", query)
        return results


class BraveSearchProvider(SearchProvider):
    name = "brave"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        if not self.api_key:
            return []
        import httpx

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": max_results},
                headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("web", {}).get("results", []):
                results.append(
                    SearchResult(
                        title=item.get("title") or "",
                        url=item.get("url") or "",
                        snippet=item.get("description") or "",
                        source=self.name,
                    )
                )
            return results


def get_search_provider() -> SearchProvider:
    from app.core.config import get_settings

    settings = get_settings()
    if settings.search_provider == "brave" and settings.brave_api_key:
        return BraveSearchProvider(settings.brave_api_key)
    return DuckDuckGoSearchProvider()

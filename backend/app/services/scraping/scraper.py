from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.services.scraping.ssrf import UnsafeURLError, validate_public_url

logger = logging.getLogger(__name__)

USER_AGENT = (
    "ScholarshipAutopilotBot/1.0 (+https://scholarship-autopilot.local; research; respectful)"
)


@dataclass
class FetchResult:
    url: str
    status_code: int
    html: str
    content_hash: str
    final_url: str
    used_playwright: bool = False


class DomainRateLimiter:
    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval
        self._last: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def wait(self, domain: str) -> None:
        async with self._lock:
            now = time.monotonic()
            last = self._last.get(domain, 0.0)
            delay = self.min_interval - (now - last)
            if delay > 0:
                await asyncio.sleep(delay)
            self._last[domain] = time.monotonic()


class ScholarshipScraper:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.rate_limiter = DomainRateLimiter(self.settings.scraper_rate_limit_per_domain)
        self._robots_cache: dict[str, RobotFileParser] = {}

    async def fetch(self, url: str, force_dynamic: bool = False) -> FetchResult:
        validate_public_url(url)
        domain = urlparse(url).netloc
        await self.rate_limiter.wait(domain)
        if not await self._allowed_by_robots(url):
            raise UnsafeURLError(f"Disallowed by robots.txt: {url}")

        if force_dynamic:
            return await self.render_dynamic_page(url)

        try:
            return await self._fetch_httpx(url)
        except Exception as exc:
            logger.warning("httpx fetch failed for %s: %s — trying Playwright", url, exc)
            return await self.render_dynamic_page(url)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def _fetch_httpx(self, url: str) -> FetchResult:
        timeout = self.settings.scraper_timeout_seconds
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        ) as client:
            response = await client.get(url)
            # Re-validate final URL after redirects
            validate_public_url(str(response.url))
            html = response.text
            return FetchResult(
                url=url,
                status_code=response.status_code,
                html=html,
                content_hash=hashlib.sha256(html.encode("utf-8", errors="ignore")).hexdigest(),
                final_url=str(response.url),
                used_playwright=False,
            )

    async def render_dynamic_page(self, url: str) -> FetchResult:
        validate_public_url(url)
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is not installed") from exc

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page(user_agent=USER_AGENT)
                response = await page.goto(
                    url, wait_until="domcontentloaded", timeout=int(self.settings.scraper_timeout_seconds * 1000)
                )
                html = await page.content()
                final_url = page.url
                validate_public_url(final_url)
                status = response.status if response else 0
                return FetchResult(
                    url=url,
                    status_code=status,
                    html=html,
                    content_hash=hashlib.sha256(html.encode("utf-8", errors="ignore")).hexdigest(),
                    final_url=final_url,
                    used_playwright=True,
                )
            finally:
                await browser.close()

    def parse(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    def extract_text(self, html: str, max_chars: int = 50000) -> str:
        soup = self.parse(html)
        for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return text[:max_chars]

    async def _allowed_by_robots(self, url: str) -> bool:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        if robots_url not in self._robots_cache:
            rp = RobotFileParser()
            try:
                async with httpx.AsyncClient(timeout=5.0, headers={"User-Agent": USER_AGENT}) as client:
                    resp = await client.get(robots_url)
                    if resp.status_code == 200:
                        rp.parse(resp.text.splitlines())
                    else:
                        rp.parse([])
            except Exception:
                rp.parse([])
            self._robots_cache[robots_url] = rp
        return self._robots_cache[robots_url].can_fetch(USER_AGENT, url)

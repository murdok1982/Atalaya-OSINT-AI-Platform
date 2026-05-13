from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
]

_TITLE_SELECTORS = [
    'meta[property="og:title"]',
    'meta[name="twitter:title"]',
    'h1.entry-title',
    'h1.article-title',
    'h1.headline',
    'h1[class*="title"]',
    'h1',
    'title',
]

_CONTENT_SELECTORS = [
    'article',
    'div[class*="article-body"]',
    'div[class*="entry-content"]',
    'div[class*="article-content"]',
    'div[class*="story-body"]',
    'div[class*="post-content"]',
    'main',
    'div[role="main"]',
]

_BLOCKED_HOSTS = {
    "localhost", "127.0.0.1", "metadata.google.internal",
    "169.254.169.254", "::1",
}


@dataclass
class ScrapedArticle:
    url: str
    final_url: str
    title: str
    content: str
    word_count: int
    domain: str
    scraped_at: str
    extraction_method: str


def _is_safe_url(url: str) -> bool:
    import ipaddress  # noqa: PLC0415
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = parsed.hostname or ""
        if not host or host.lower() in _BLOCKED_HOSTS:
            return False
        try:
            addr = ipaddress.ip_address(host)
            private_nets = [
                ipaddress.ip_network(n) for n in
                ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8"]
            ]
            return not any(addr in net for net in private_nets)
        except ValueError:
            lower = host.lower()
            return not lower.endswith((".local", ".internal", ".localhost", ".localdomain"))
    except Exception:
        return False


class NewsArticleScraper:
    """
    Resilient article scraper with multi-selector extraction,
    trafilatura primary and BeautifulSoup fallback.
    """

    def __init__(self, max_retries: int = 3, base_delay: float = 1.5) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay

    def _random_headers(self) -> dict[str, str]:
        return {
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.7,en;q=0.5",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def fetch_html(self, url: str, client: httpx.AsyncClient) -> tuple[str, str] | None:
        """Returns (html, final_url) or None on failure."""
        if not _is_safe_url(url):
            logger.warning("scraper_blocked_url", url=url)
            return None

        for attempt in range(self.max_retries):
            try:
                resp = await client.get(
                    url,
                    headers=self._random_headers(),
                    timeout=30,
                    follow_redirects=True,
                )
                if resp.status_code == 429:
                    wait = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning("scraper_rate_limited", url=url, wait=wait)
                    await asyncio.sleep(wait)
                    continue
                if resp.status_code in (403, 451):
                    logger.warning("scraper_blocked", url=url, status=resp.status_code)
                    return None
                resp.raise_for_status()
                return resp.text, str(resp.url)
            except httpx.HTTPStatusError as exc:
                if attempt == self.max_retries - 1:
                    logger.warning("scraper_http_error", url=url, status=exc.response.status_code)
                    return None
            except Exception as exc:
                wait = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait)
                else:
                    logger.warning("scraper_fetch_failed", url=url, error=str(exc))
                    return None
        return None

    def _extract_with_trafilatura(self, html: str) -> tuple[str, str]:
        """Returns (content, title)."""
        try:
            import trafilatura  # noqa: PLC0415
            content = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
            meta = trafilatura.extract_metadata(html)
            title = meta.title if meta and meta.title else ""
            return content, title
        except Exception:
            return "", ""

    def _extract_with_bs4(self, html: str, url: str) -> tuple[str, str]:
        """Returns (content, title) using multi-selector BeautifulSoup strategy."""
        try:
            from bs4 import BeautifulSoup  # noqa: PLC0415
            soup = BeautifulSoup(html, "html.parser")

            for tag in soup(["script", "style", "nav", "footer", "aside", "header",
                              "iframe", "noscript", "form", "button", "figure"]):
                tag.decompose()

            # Title extraction
            title = ""
            for sel in _TITLE_SELECTORS:
                elem = soup.select_one(sel)
                if elem:
                    title = elem.get("content") or elem.get_text(strip=True)
                    if title:
                        break

            # Content extraction
            content = ""
            for sel in _CONTENT_SELECTORS:
                elem = soup.select_one(sel)
                if elem:
                    content = elem.get_text(separator="\n", strip=True)
                    if len(content) > 200:
                        break

            if not content:
                content = soup.get_text(separator="\n", strip=True)

            return content[:8000], title.strip()
        except Exception as exc:
            logger.warning("bs4_extract_failed", url=url, error=str(exc))
            return "", ""

    async def scrape_article(self, url: str, client: httpx.AsyncClient | None = None) -> ScrapedArticle | None:
        """Scrape a single article URL. Creates its own client if none provided."""
        own_client = client is None
        if own_client:
            client = httpx.AsyncClient(follow_redirects=True)

        try:
            result = await self.fetch_html(url, client)
            if not result:
                return None
            html, final_url = result

            # Try trafilatura first, fall back to BS4
            content, title = self._extract_with_trafilatura(html)
            method = "trafilatura"
            if not content or len(content) < 100:
                content, title_bs = self._extract_with_bs4(html, url)
                method = "beautifulsoup"
                if not title:
                    title = title_bs

            if not content:
                return None

            return ScrapedArticle(
                url=url,
                final_url=final_url,
                title=title,
                content=content,
                word_count=len(content.split()),
                domain=urlparse(final_url).netloc,
                scraped_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                extraction_method=method,
            )
        finally:
            if own_client:
                await client.aclose()

    async def scrape_batch(
        self,
        urls: list[str],
        max_concurrent: int = 5,
        delay_between: float = 1.0,
    ) -> list[ScrapedArticle]:
        """Scrape multiple URLs with concurrency control."""
        semaphore = asyncio.Semaphore(max_concurrent)
        results: list[ScrapedArticle] = []

        async def scrape_one(url: str, client: httpx.AsyncClient) -> ScrapedArticle | None:
            async with semaphore:
                article = await self.scrape_article(url, client)
                await asyncio.sleep(delay_between + random.uniform(0, 0.5))
                return article

        async with httpx.AsyncClient(follow_redirects=True) as client:
            tasks = [scrape_one(u, client) for u in urls]
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in raw_results:
            if isinstance(r, ScrapedArticle):
                results.append(r)
            elif isinstance(r, Exception):
                logger.warning("scrape_batch_error", error=str(r))

        logger.info("scrape_batch_done", total=len(urls), success=len(results))
        return results

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AtalayaGeointBot/1.0; +https://atalaya.local)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*;q=0.8",
}

_MAX_ITEMS_PER_FEED = 20
_FEED_TIMEOUT_SECONDS = 20
_CONCURRENT_FEEDS = 8


@dataclass
class FeedItem:
    id: str
    title: str
    url: str
    summary: str
    published: datetime | None
    source_id: str
    source_name: str
    language: str
    reliability: str
    categories: list[str]
    regions: list[str]
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "published": self.published.isoformat() if self.published else None,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "language": self.language,
            "reliability": self.reliability,
            "categories": self.categories,
            "regions": self.regions,
        }


class RSSAggregator:
    """Async RSS/Atom feed aggregator with deduplication and rate limiting."""

    def __init__(self, rate_limit_per_second: float = 2.0) -> None:
        self._rate_limit = rate_limit_per_second
        self._seen_ids: set[str] = set()

    def _deduplicate_id(self, url: str, title: str) -> str:
        return hashlib.sha256(f"{url}|{title}".encode()).hexdigest()[:16]

    async def _fetch_feed(self, client: httpx.AsyncClient, source: dict) -> list[FeedItem]:
        feed_url = source["url"]
        source_id = source["id"]
        source_name = source["name"]

        try:
            resp = await client.get(feed_url, timeout=_FEED_TIMEOUT_SECONDS, headers=_DEFAULT_HEADERS)
            resp.raise_for_status()
            raw_xml = resp.text
        except Exception as exc:
            logger.warning("rss_fetch_failed", source_id=source_id, url=feed_url, error=str(exc))
            return []

        try:
            import feedparser  # type: ignore[import]
            parsed = feedparser.parse(raw_xml)
        except Exception as exc:
            logger.warning("rss_parse_failed", source_id=source_id, error=str(exc))
            return []

        items: list[FeedItem] = []
        for entry in parsed.entries[:_MAX_ITEMS_PER_FEED]:
            title = getattr(entry, "title", "") or ""
            link = getattr(entry, "link", "") or ""
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""

            # Parse publication date
            published: datetime | None = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                except Exception:
                    pass

            item_id = self._deduplicate_id(link, title)
            if item_id in self._seen_ids:
                continue
            self._seen_ids.add(item_id)

            # Strip HTML from summary
            if summary:
                try:
                    from bs4 import BeautifulSoup  # noqa: PLC0415
                    summary = BeautifulSoup(summary, "html.parser").get_text(separator=" ", strip=True)[:500]
                except Exception:
                    summary = summary[:500]

            items.append(FeedItem(
                id=item_id,
                title=title.strip(),
                url=link,
                summary=summary,
                published=published,
                source_id=source_id,
                source_name=source_name,
                language=source.get("language", "en"),
                reliability=source.get("reliability", "U"),
                categories=source.get("categories", []),
                regions=source.get("regions", ["global"]),
            ))

        logger.info("rss_fetched", source_id=source_id, items=len(items))
        return items

    async def collect_from_sources(
        self,
        sources: list[dict],
        category_filter: list[str] | None = None,
        region_filter: list[str] | None = None,
        since: datetime | None = None,
    ) -> list[FeedItem]:
        """Fetch all active feeds concurrently, apply optional filters."""
        active = [s for s in sources if s.get("active", True)]

        if category_filter:
            active = [s for s in active if any(c in s.get("categories", []) for c in category_filter)]
        if region_filter:
            active = [s for s in active if any(r in s.get("regions", []) for r in region_filter)]

        semaphore = asyncio.Semaphore(_CONCURRENT_FEEDS)

        async def bounded_fetch(client: httpx.AsyncClient, source: dict) -> list[FeedItem]:
            async with semaphore:
                result = await self._fetch_feed(client, source)
                await asyncio.sleep(1.0 / self._rate_limit)
                return result

        all_items: list[FeedItem] = []
        async with httpx.AsyncClient(follow_redirects=True) as client:
            tasks = [bounded_fetch(client, src) for src in active]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, list):
                all_items.extend(res)
            elif isinstance(res, Exception):
                logger.warning("rss_task_exception", error=str(res))

        if since:
            all_items = [
                item for item in all_items
                if item.published and item.published >= since
            ]

        # Sort newest first
        all_items.sort(
            key=lambda x: x.published or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        logger.info("rss_collection_complete", total_items=len(all_items), feeds_queried=len(active))
        return all_items

    def clear_seen(self) -> None:
        self._seen_ids.clear()

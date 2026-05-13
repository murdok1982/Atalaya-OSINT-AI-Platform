from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

# YouTube RSS feed requires no API key and returns the last 15 videos per channel
_YT_RSS_TEMPLATE = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
_YT_VIDEO_BASE = "https://www.youtube.com/watch?v="
_TIMEOUT = 15


@dataclass
class YouTubeVideoMetadata:
    video_id: str
    title: str
    url: str
    published: datetime | None
    description: str
    channel_id: str
    channel_name: str
    language: str
    reliability: str
    categories: list[str]
    regions: list[str]

    def to_dict(self) -> dict:
        return {
            "video_id": self.video_id,
            "title": self.title,
            "url": self.url,
            "published": self.published.isoformat() if self.published else None,
            "description": self.description,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "language": self.language,
            "reliability": self.reliability,
            "categories": self.categories,
            "regions": self.regions,
            "source_type": "youtube",
        }


class YouTubeOSINTCollector:
    """
    Collects video metadata from YouTube channels via RSS (no API key needed).
    Optional YouTube Data API v3 support when YOUTUBE_API_KEY is configured.
    """

    def __init__(self, api_key: str = "", max_per_channel: int = 10) -> None:
        self.api_key = api_key
        self.max_per_channel = max_per_channel

    async def _fetch_channel_rss(
        self,
        client: httpx.AsyncClient,
        channel: dict,
    ) -> list[YouTubeVideoMetadata]:
        channel_id = channel["channel_id"]
        rss_url = _YT_RSS_TEMPLATE.format(channel_id=channel_id)

        try:
            resp = await client.get(rss_url, timeout=_TIMEOUT)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("yt_rss_failed", channel_id=channel_id, error=str(exc))
            return []

        try:
            import feedparser  # type: ignore[import]
            parsed = feedparser.parse(resp.text)
        except Exception as exc:
            logger.warning("yt_rss_parse_failed", channel_id=channel_id, error=str(exc))
            return []

        videos: list[YouTubeVideoMetadata] = []
        for entry in parsed.entries[: self.max_per_channel]:
            video_id = getattr(entry, "yt_videoid", "") or ""
            if not video_id:
                link = getattr(entry, "link", "")
                if "watch?v=" in link:
                    video_id = link.split("watch?v=")[-1].split("&")[0]

            title = getattr(entry, "title", "") or ""
            description = ""
            if hasattr(entry, "summary"):
                description = entry.summary[:500]
            elif hasattr(entry, "media_description"):
                description = entry.media_description[:500]

            published: datetime | None = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                except Exception:
                    pass

            if not video_id or not title:
                continue

            videos.append(YouTubeVideoMetadata(
                video_id=video_id,
                title=title.strip(),
                url=f"{_YT_VIDEO_BASE}{video_id}",
                published=published,
                description=description.strip(),
                channel_id=channel_id,
                channel_name=channel.get("name", ""),
                language=channel.get("language", "en"),
                reliability=channel.get("reliability", "U"),
                categories=channel.get("categories", []),
                regions=channel.get("regions", ["global"]),
            ))

        logger.info("yt_channel_fetched", channel_id=channel_id, videos=len(videos))
        return videos

    async def collect_from_channels(
        self,
        channels: list[dict],
        category_filter: list[str] | None = None,
        since: datetime | None = None,
    ) -> list[YouTubeVideoMetadata]:
        """Collect video metadata from all active channels concurrently."""
        active = [c for c in channels if c.get("active", True)]

        if category_filter:
            active = [
                c for c in active
                if any(cat in c.get("categories", []) for cat in category_filter)
            ]

        semaphore = asyncio.Semaphore(4)

        async def bounded_fetch(client: httpx.AsyncClient, ch: dict) -> list[YouTubeVideoMetadata]:
            async with semaphore:
                result = await self._fetch_channel_rss(client, ch)
                await asyncio.sleep(0.5)
                return result

        all_videos: list[YouTubeVideoMetadata] = []
        async with httpx.AsyncClient(follow_redirects=True) as client:
            tasks = [bounded_fetch(client, ch) for ch in active]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, list):
                all_videos.extend(res)

        if since:
            all_videos = [
                v for v in all_videos
                if v.published and v.published >= since
            ]

        all_videos.sort(
            key=lambda v: v.published or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        logger.info("yt_collection_complete", total_videos=len(all_videos), channels=len(active))
        return all_videos

    def format_for_analysis(self, videos: list[YouTubeVideoMetadata], max_items: int = 20) -> str:
        """Format video metadata as text context for LLM analysis."""
        lines: list[str] = []
        for v in videos[:max_items]:
            date_str = v.published.strftime("%Y-%m-%d") if v.published else "fecha desconocida"
            lines.append(
                f"[VIDEO] {v.channel_name} ({date_str})\n"
                f"Título: {v.title}\n"
                f"Descripción: {v.description}\n"
                f"URL: {v.url}\n"
                f"Fiabilidad: {v.reliability}\n"
            )
        return "\n---\n".join(lines)

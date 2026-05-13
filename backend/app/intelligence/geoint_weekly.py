from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.adapter import LLMAdapter
from app.llm.providers.base import LLMMessage
from app.llm.prompts.geoint import (
    DEFENSE_ANALYSIS_PROMPT,
    ECONOMIC_ANALYSIS_PROMPT,
    EXECUTIVE_SUMMARY_PROMPT,
    GEOINT_SYSTEM_PROMPT,
    INTELLIGENCE_ANALYSIS_PROMPT,
    METHODOLOGY_NOTE,
    SECURITY_ANALYSIS_PROMPT,
)
from app.scrapers.rss_aggregator import FeedItem, RSSAggregator
from app.scrapers.youtube_osint import YouTubeOSINTCollector, YouTubeVideoMetadata

logger = get_logger(__name__)

ReportCategory = Literal["economics", "security", "defense", "intelligence"]

CATEGORY_PROMPTS: dict[ReportCategory, str] = {
    "economics": ECONOMIC_ANALYSIS_PROMPT,
    "security": SECURITY_ANALYSIS_PROMPT,
    "defense": DEFENSE_ANALYSIS_PROMPT,
    "intelligence": INTELLIGENCE_ANALYSIS_PROMPT,
}

_MAX_CONTEXT_CHARS = 12000
_MAX_ITEMS_PER_CATEGORY = 30


@dataclass
class CategoryAnalysis:
    category: ReportCategory
    content: str
    sources_count: int
    reliability_breakdown: dict[str, int]
    duration_seconds: float


@dataclass
class WeeklyIntelReport:
    period_start: datetime
    period_end: datetime
    generated_at: datetime
    executive_summary: str
    categories: dict[ReportCategory, CategoryAnalysis]
    model_used: str
    classification: str
    total_sources: int
    file_path: str | None = None

    def to_dict(self) -> dict:
        return {
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
            },
            "generated_at": self.generated_at.isoformat(),
            "model_used": self.model_used,
            "classification": self.classification,
            "total_sources": self.total_sources,
            "executive_summary": self.executive_summary,
            "categories": {
                cat: {
                    "content": analysis.content,
                    "sources_count": analysis.sources_count,
                    "reliability_breakdown": analysis.reliability_breakdown,
                    "duration_seconds": round(analysis.duration_seconds, 2),
                }
                for cat, analysis in self.categories.items()
            },
        }


def _load_sources() -> dict:
    sources_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "config", "geoint_sources.json"
    )
    sources_path = os.path.normpath(sources_path)
    if not os.path.exists(sources_path):
        logger.warning("geoint_sources_not_found", path=sources_path)
        return {"rss_feeds": {}, "youtube_channels": {}}
    with open(sources_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _build_rss_source_list(sources: dict) -> list[dict]:
    """Flatten all RSS feed groups into a single list."""
    result: list[dict] = []
    for group in sources.get("rss_feeds", {}).values():
        result.extend(group)
    return result


def _build_yt_channel_list(sources: dict) -> list[dict]:
    result: list[dict] = []
    for group in sources.get("youtube_channels", {}).values():
        result.extend(group)
    return result


def _cluster_by_category(
    items: list[FeedItem | YouTubeVideoMetadata],
    categories: list[ReportCategory],
) -> dict[ReportCategory, list]:
    """Assign each item to all matching categories."""
    clusters: dict[ReportCategory, list] = {cat: [] for cat in categories}
    for item in items:
        item_cats = item.categories if hasattr(item, "categories") else []
        for cat in categories:
            if cat in item_cats:
                clusters[cat].append(item)
    return clusters


def _reliability_breakdown(items: list) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        rel = getattr(item, "reliability", "U")
        counts[rel] = counts.get(rel, 0) + 1
    return counts


def _build_context_text(items: list, max_chars: int = _MAX_CONTEXT_CHARS) -> str:
    """Convert a list of feed/video items to a text context block for LLM."""
    lines: list[str] = []
    total_chars = 0

    for item in items[:_MAX_ITEMS_PER_CATEGORY]:
        if hasattr(item, "summary"):
            # FeedItem
            date_str = item.published.strftime("%Y-%m-%d") if item.published else "fecha desconocida"
            block = (
                f"[{item.reliability}] {item.source_name} ({date_str})\n"
                f"Título: {item.title}\n"
                f"Resumen: {item.summary[:300]}\n"
                f"URL: {item.url}\n"
            )
        else:
            # YouTubeVideoMetadata
            date_str = item.published.strftime("%Y-%m-%d") if item.published else "fecha desconocida"
            block = (
                f"[{item.reliability}] YouTube/{item.channel_name} ({date_str})\n"
                f"Título: {item.title}\n"
                f"Descripción: {item.description[:300]}\n"
                f"URL: {item.url}\n"
            )

        if total_chars + len(block) > max_chars:
            break
        lines.append(block)
        total_chars += len(block)

    return "\n---\n".join(lines)


def _period_string(start: datetime, end: datetime) -> str:
    return f"{start.strftime('%d %b %Y')} — {end.strftime('%d %b %Y')}"


class WeeklyGeointPipeline:
    """
    Orchestrates the full weekly geopolitical intelligence report:
    1. Collect RSS + YouTube OSINT
    2. Cluster by category
    3. Analyze each category with local LLM
    4. Generate executive summary
    5. Assemble and persist final report
    """

    def __init__(self, llm_adapter: LLMAdapter | None = None) -> None:
        self.llm = llm_adapter or LLMAdapter(settings)
        self.rss = RSSAggregator(rate_limit_per_second=2.0)
        self.yt = YouTubeOSINTCollector(
            api_key=getattr(settings, "YOUTUBE_API_KEY", ""),
            max_per_channel=10,
        )
        self.categories: list[ReportCategory] = ["economics", "security", "defense", "intelligence"]

    async def _analyze_category(
        self,
        category: ReportCategory,
        items: list,
        period: str,
    ) -> CategoryAnalysis:
        t0 = time.monotonic()
        context = _build_context_text(items)

        if not context.strip():
            logger.warning("geoint_no_context", category=category)
            return CategoryAnalysis(
                category=category,
                content=f"## Sin datos disponibles para {category} en este período.",
                sources_count=0,
                reliability_breakdown={},
                duration_seconds=time.monotonic() - t0,
            )

        prompt_template = CATEGORY_PROMPTS[category]
        user_prompt = prompt_template.format(period=period, context=context)

        messages = [
            LLMMessage(role="system", content=GEOINT_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt),
        ]

        try:
            response = await self.llm.complete(
                messages=messages,
                provider=getattr(settings, "GEOINT_LLM_PROVIDER", settings.LLM_DEFAULT_PROVIDER),
                model=getattr(settings, "GEOINT_LLM_MODEL", settings.LLM_DEFAULT_MODEL),
                max_tokens=2000,
                temperature=0.2,
                timeout=180,
                fallback=True,
            )
            content = response.content
        except Exception as exc:
            logger.error("geoint_llm_failed", category=category, error=str(exc))
            content = f"[ERROR] Análisis no disponible para {category}: {exc}"

        return CategoryAnalysis(
            category=category,
            content=content,
            sources_count=len(items),
            reliability_breakdown=_reliability_breakdown(items),
            duration_seconds=time.monotonic() - t0,
        )

    async def _generate_executive_summary(
        self,
        category_analyses: dict[ReportCategory, CategoryAnalysis],
        period: str,
    ) -> str:
        sector_text = "\n\n".join(
            f"### {cat.upper()}\n{analysis.content[:1500]}"
            for cat, analysis in category_analyses.items()
            if analysis.content
        )

        messages = [
            LLMMessage(role="system", content=GEOINT_SYSTEM_PROMPT),
            LLMMessage(
                role="user",
                content=EXECUTIVE_SUMMARY_PROMPT.format(
                    period=period,
                    sector_analyses=sector_text,
                ),
            ),
        ]

        try:
            response = await self.llm.complete(
                messages=messages,
                provider=getattr(settings, "GEOINT_LLM_PROVIDER", settings.LLM_DEFAULT_PROVIDER),
                model=getattr(settings, "GEOINT_LLM_MODEL", settings.LLM_DEFAULT_MODEL),
                max_tokens=1200,
                temperature=0.2,
                timeout=180,
                fallback=True,
            )
            return response.content
        except Exception as exc:
            logger.error("geoint_summary_failed", error=str(exc))
            return f"[ERROR] Resumen ejecutivo no disponible: {exc}"

    async def run(
        self,
        days_back: int = 7,
        category_filter: list[ReportCategory] | None = None,
        region_filter: list[str] | None = None,
        classification: str | None = None,
    ) -> WeeklyIntelReport:
        t_total = time.monotonic()
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=days_back)
        period_str = _period_string(start_dt, end_dt)
        active_categories = category_filter or self.categories
        classification = classification or getattr(settings, "DEFAULT_CLASSIFICATION", "UNCLASSIFIED")

        logger.info("geoint_pipeline_start", period=period_str, categories=active_categories)

        # --- Phase 1: OSINT Collection ---
        sources = _load_sources()
        rss_sources = _build_rss_source_list(sources)
        yt_channels = _build_yt_channel_list(sources)

        logger.info("geoint_collecting_rss", sources=len(rss_sources))
        feed_items = await self.rss.collect_from_sources(
            rss_sources,
            category_filter=active_categories,
            region_filter=region_filter,
            since=start_dt,
        )

        logger.info("geoint_collecting_youtube", channels=len(yt_channels))
        yt_videos = await self.yt.collect_from_channels(
            yt_channels,
            category_filter=active_categories,
            since=start_dt,
        )

        all_items: list = list(feed_items) + list(yt_videos)
        total_sources = len(all_items)
        logger.info("geoint_collection_done", total_items=total_sources)

        # --- Phase 2: Cluster by category ---
        clusters = _cluster_by_category(all_items, active_categories)

        # --- Phase 3: Per-category analysis ---
        category_results: dict[ReportCategory, CategoryAnalysis] = {}
        for cat in active_categories:
            logger.info("geoint_analyzing_category", category=cat, items=len(clusters[cat]))
            analysis = await self._analyze_category(cat, clusters[cat], period_str)
            category_results[cat] = analysis

        # --- Phase 4: Executive summary ---
        logger.info("geoint_generating_summary")
        summary = await self._generate_executive_summary(category_results, period_str)

        # --- Phase 5: Assemble and persist ---
        model_id = getattr(settings, "GEOINT_LLM_MODEL", settings.LLM_DEFAULT_MODEL)
        methodology = METHODOLOGY_NOTE.format(
            classification=classification,
            model=model_id,
            generated_at=end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        full_markdown = _assemble_markdown(summary, category_results, methodology)
        file_path = _save_report(full_markdown, end_dt, classification)

        report = WeeklyIntelReport(
            period_start=start_dt,
            period_end=end_dt,
            generated_at=end_dt,
            executive_summary=summary,
            categories=category_results,
            model_used=model_id,
            classification=classification,
            total_sources=total_sources,
            file_path=file_path,
        )

        logger.info(
            "geoint_pipeline_done",
            file=file_path,
            total_sources=total_sources,
            duration_s=round(time.monotonic() - t_total, 1),
        )
        return report


def _assemble_markdown(
    summary: str,
    categories: dict[ReportCategory, CategoryAnalysis],
    methodology: str,
) -> str:
    parts = [
        "# INFORME DE INTELIGENCIA GEOPOLÍTICA SEMANAL\n",
        summary,
        "\n---\n",
    ]
    for cat, analysis in categories.items():
        parts.append(analysis.content)
        parts.append("\n---\n")
    parts.append(methodology)
    return "\n".join(parts)


def _save_report(content: str, dt: datetime, classification: str) -> str:
    base_path = getattr(settings, "REPORTS_STORAGE_PATH", "./data/reports")
    geoint_dir = os.path.join(base_path, "geoint")
    os.makedirs(geoint_dir, exist_ok=True)

    filename = f"geoint_weekly_{dt.strftime('%Y%m%d_%H%M%S')}_{classification.lower()}.md"
    file_path = os.path.join(geoint_dir, filename)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info("geoint_report_saved", path=file_path, size_kb=round(len(content) / 1024, 1))
    return file_path

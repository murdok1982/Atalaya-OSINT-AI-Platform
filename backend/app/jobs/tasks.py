from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


async def enqueue_job(job: Any) -> str:
    """Enqueue a job to ARQ. Returns ARQ job ID."""
    from app.db.session import redis_client  # noqa: PLC0415
    from arq import create_pool  # noqa: PLC0415
    from arq.connections import RedisSettings  # noqa: PLC0415
    from app.core.config import settings  # noqa: PLC0415

    pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    arq_job = await pool.enqueue_job(
        "run_coordinator_job",
        job_id=str(job.id),
        case_id=str(job.case_id),
        task_description=job.input_params.get("task_description", ""),
        operator_id=str(job.created_by),
    )
    await pool.aclose()
    return arq_job.job_id if arq_job else str(uuid.uuid4())


async def run_coordinator_job(
    ctx: dict,
    job_id: str,
    case_id: str,
    task_description: str,
    operator_id: str,
) -> dict:
    """ARQ task: run coordinator agent for a job."""
    from app.db.session import AsyncSessionLocal  # noqa: PLC0415
    from app.models.job import Job, JobStatus  # noqa: PLC0415
    from app.models.evidence import Evidence, EvidenceType  # noqa: PLC0415
    from app.models.entity import Entity  # noqa: PLC0415
    from app.agents.coordinator import CoordinatorAgent  # noqa: PLC0415
    from app.agents.base import AgentContext  # noqa: PLC0415
    from app.llm.adapter import LLMAdapter  # noqa: PLC0415
    from app.tools.base import build_default_registry  # noqa: PLC0415
    from app.core.config import settings  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415
    import json  # noqa: PLC0415

    logger.info("job_starting", job_id=job_id, case_id=case_id)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            logger.error("job_not_found", job_id=job_id)
            return {"error": "Job not found"}

        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            llm = LLMAdapter(settings)
            tools = build_default_registry(settings)
            coordinator = CoordinatorAgent(llm_adapter=llm, tool_registry=tools)

            agent_context = AgentContext(
                case_id=case_id,
                job_id=job_id,
                operator_id=operator_id,
                scope=["public_sources"],
                input_data={"task_description": task_description},
            )

            agent_result = await coordinator.run(agent_context)

            # Persist findings as evidence
            for finding in agent_result.findings:
                ev = Evidence(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    title=f"{finding.finding_type}: {finding.source[:100]}",
                    evidence_type=_map_finding_to_evidence_type(finding.finding_type),
                    source_url=finding.source,
                    content_text=json.dumps(finding.data, default=str)[:10000],
                    raw_data=finding.data,
                    collected_at=finding.timestamp_collected,
                    collected_by=f"agent:{agent_result.agent.value}",
                    confidence_score=finding.confidence,
                )
                db.add(ev)

            # Persist extracted entities
            for ent_data in agent_result.entities_extracted:
                ent = Entity(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    entity_type=ent_data.get("entity_type", "DOMAIN"),
                    value=ent_data.get("value", ""),
                    display_name=ent_data.get("display_name", ent_data.get("value", "")),
                    confidence_score=ent_data.get("confidence_score", 0.7),
                    attributes=ent_data.get("attributes", {}),
                )
                db.add(ent)

            completed_at = datetime.now(timezone.utc)
            duration = (completed_at - job.started_at).total_seconds()

            job.status = JobStatus.COMPLETED
            job.completed_at = completed_at
            job.duration_seconds = duration
            job.findings_count = len(agent_result.findings)
            job.result_summary = agent_result.raw_output[:500] if agent_result.raw_output else f"Collected {len(agent_result.findings)} findings"
            await db.commit()

            logger.info("job_completed", job_id=job_id, findings=len(agent_result.findings), duration_s=duration)
            return {"success": True, "findings_count": len(agent_result.findings)}

        except Exception as exc:
            logger.error("job_failed", job_id=job_id, error=str(exc))
            job.status = JobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            return {"error": str(exc)}


def _map_finding_to_evidence_type(finding_type: str) -> str:
    mapping = {
        "dns_lookup": "DNS_RECORD",
        "whois_query": "WHOIS",
        "cert_search": "CERTIFICATE",
        "web_fetch": "URL",
        "web_search": "URL",
        "social_profile_fetch": "SOCIAL_POST",
        "document_extract": "DOCUMENT",
        "archive_lookup": "URL",
        "ip_geolocation": "METADATA",
    }
    return mapping.get(finding_type, "TEXT")

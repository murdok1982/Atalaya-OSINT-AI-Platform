from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, ClassVar

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EventType(str, Enum):
    CASE_CREATED = "case.created"
    CASE_UPDATED = "case.updated"
    CASE_CLOSED = "case.closed"
    JOB_STARTED = "job.started"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    EVIDENCE_COLLECTED = "evidence.collected"
    EVIDENCE_INDEXED = "evidence.indexed"
    ENTITY_RESOLVED = "entity.resolved"
    REPORT_GENERATED = "report.generated"
    ALERT_TRIGGERED = "alert.triggered"
    THREAT_DETECTED = "threat.detected"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    AUDIT_EVENT = "audit.event"
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    TOOL_EXECUTED = "tool.executed"
    CLASSIFICATION_CHANGED = "classification.changed"
    TENANT_ISOLATION_BREACH = "tenant.isolation.breach"


@dataclass
class AtalayaEvent:
    event_type: EventType
    source: str
    data: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    tenant_id: str = ""
    correlation_id: str = ""
    classification: str = "UNCLASSIFIED"
    version: str = "2.0.0"

    def to_json(self) -> str:
        return json.dumps({
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
            "tenant_id": self.tenant_id,
            "correlation_id": self.correlation_id,
            "classification": self.classification,
            "version": self.version,
        })

    @classmethod
    def from_json(cls, json_str: str) -> "AtalayaEvent":
        d = json.loads(json_str)
        return cls(
            event_type=EventType(d["event_type"]),
            source=d["source"],
            data=d["data"],
            event_id=d.get("event_id", str(uuid.uuid4())),
            timestamp=d.get("timestamp", time.time()),
            tenant_id=d.get("tenant_id", ""),
            correlation_id=d.get("correlation_id", ""),
            classification=d.get("classification", "UNCLASSIFIED"),
        )


class EventBus:
    """Event bus with Kafka integration and local fallback."""

    _handlers: ClassVar[dict[str, list[Callable]]] = {}
    _kafka_producer: Any = None
    _initialized: bool = False

    @classmethod
    async def initialize(cls) -> None:
        if cls._initialized:
            return
        if settings.has_kafka:
            try:
                from aiokafka import AIOKafkaProducer
                cls._kafka_producer = AIOKafkaProducer(
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: v.encode("utf-8"),
                )
                await cls._kafka_producer.start()
                logger.info("kafka_producer_started", brokers=settings.KAFKA_BOOTSTRAP_SERVERS)
            except Exception as exc:
                logger.error("kafka_init_failed", error=str(exc))
                cls._kafka_producer = None
        cls._initialized = True

    @classmethod
    async def shutdown(cls) -> None:
        if cls._kafka_producer:
            try:
                await cls._kafka_producer.stop()
            except Exception as exc:
                logger.error("kafka_shutdown_failed", error=str(exc))
        cls._initialized = False

    @classmethod
    def register_handler(cls, event_type: EventType, handler: Callable) -> None:
        key = event_type.value
        if key not in cls._handlers:
            cls._handlers[key] = []
        cls._handlers[key].append(handler)
        logger.info("event_handler_registered", event_type=key)

    @classmethod
    async def publish(cls, event: AtalayaEvent) -> None:
        if not cls._initialized:
            await cls.initialize()

        logger.info("event_published", event_type=event.event_type.value, event_id=event.event_id)

        if cls._kafka_producer:
            try:
                await cls._kafka_producer.send_and_wait(
                    settings.KAFKA_EVENTS_TOPIC,
                    key=event.event_id.encode("utf-8"),
                    value=event.to_json(),
                )
            except Exception as exc:
                logger.error("kafka_publish_failed", error=str(exc), event_type=event.event_type.value)

        handlers = cls._handlers.get(event.event_type.value, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as exc:
                logger.error("event_handler_failed", handler=handler.__name__, error=str(exc))

    @classmethod
    async def publish_alert(cls, event: AtalayaEvent) -> None:
        if cls._kafka_producer:
            try:
                await cls._kafka_producer.send_and_wait(
                    settings.KAFKA_ALERTS_TOPIC,
                    key=event.event_id.encode("utf-8"),
                    value=event.to_json(),
                )
            except Exception as exc:
                logger.error("kafka_alert_publish_failed", error=str(exc))


event_bus = EventBus()

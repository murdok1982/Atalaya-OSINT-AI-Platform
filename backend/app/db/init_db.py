from __future__ import annotations

from app.core.logging import get_logger
from app.db.session import Base, engine

logger = get_logger(__name__)


async def create_all_tables() -> None:
    # Import all models so they register with Base.metadata
    import app.models.user  # noqa: F401
    import app.models.case  # noqa: F401
    import app.models.entity  # noqa: F401
    import app.models.evidence  # noqa: F401
    import app.models.job  # noqa: F401
    import app.models.report  # noqa: F401
    import app.models.audit_log  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("tables_created")


async def drop_all_tables() -> None:
    """For testing only."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("all_tables_dropped")


async def seed_admin_user() -> None:
    from app.db.session import AsyncSessionLocal  # noqa: PLC0415
    from app.models.user import User  # noqa: PLC0415
    from app.core.security import get_password_hash  # noqa: PLC0415
    from sqlalchemy import select  # noqa: PLC0415
    import uuid  # noqa: PLC0415

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            return

        admin = User(
            id=str(uuid.uuid4()),
            username="admin",
            email="admin@atalaya.local",
            hashed_password=get_password_hash("atalaya_admin_2024!"),
            full_name="Atalaya Administrator",
            is_active=True,
            is_superuser=True,
            scopes=["admin", "read:cases", "write:cases", "read:reports", "write:reports", "execute:jobs"],
        )
        db.add(admin)
        await db.commit()
        logger.warning(
            "default_admin_created",
            username="admin",
            note="CHANGE THE DEFAULT PASSWORD IMMEDIATELY",
        )

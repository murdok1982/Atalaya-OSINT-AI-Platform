#!/usr/bin/env python3
"""Seed the database with default admin user and sample data."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.core.security import get_password_hash
from app.db.session import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select


async def seed() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        # Check if admin already exists
        result = await session.execute(select(User).where(User.username == "admin"))
        existing = result.scalar_one_or_none()
        if existing:
            print("[INFO] Admin user already exists — skipping seed.")
            return

        admin = User(
            username="admin",
            email="admin@atalaya.local",
            hashed_password=get_password_hash("admin"),
            full_name="Atalaya Administrator",
            is_active=True,
            is_superuser=True,
            scopes=["read", "write", "admin"],
        )
        session.add(admin)
        await session.commit()
        print("[OK] Admin user created:")
        print("     Username: admin")
        print("     Password: admin")
        print("     ⚠  Change the password immediately after first login!")


if __name__ == "__main__":
    asyncio.run(seed())

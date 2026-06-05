import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "admin@manifesto.local"))
        existing = result.scalar_one_or_none()
        if existing:
            print("Seed skipped — user already exists")
            return
        user = User(
            name="Admin",
            email="admin@manifesto.local",
            password_hash=hash_password("admin123"),
            role="admin",
        )
        session.add(user)
        await session.commit()
        print("Seed complete — admin@manifesto.local created")


if __name__ == "__main__":
    asyncio.run(seed())

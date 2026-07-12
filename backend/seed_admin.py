"""
Run once to create the initial admin user:
    python seed_admin.py
"""
import asyncio
from database import init_db, AsyncSessionLocal
from models import User
from auth import hash_password


async def main():
    await init_db()
    async with AsyncSessionLocal() as db:
        admin = User(
            username="admin",
            email="admin@football.watch",
            hashed_password=hash_password("ChangeMe123!"),
            is_admin=True,
        )
        db.add(admin)
        await db.commit()
        print("Admin user created — username: admin  password: ChangeMe123!")


if __name__ == "__main__":
    asyncio.run(main())

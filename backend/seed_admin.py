"""
Create (or upgrade) the superuser account:
    python seed_admin.py                       -> admin / ChangeMe123!
    python seed_admin.py alice alice@x.com pw  -> named account

Safe to re-run: an existing account with that username is promoted to superuser
rather than duplicated. Change the password immediately after the first login.
"""
import asyncio
import sys

from sqlalchemy import select

from database import init_db, AsyncSessionLocal
from models import User
from auth import hash_password


async def main(username: str, email: str, password: str):
    await init_db()
    async with AsyncSessionLocal() as db:
        existing = (await db.execute(
            select(User).where(User.username == username)
        )).scalar_one_or_none()

        if existing:
            existing.is_admin = True
            existing.is_superuser = True
            existing.tier = "premium"
            await db.commit()
            print(f"Promoted existing user '{username}' to superuser.")
            return

        db.add(User(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            is_admin=True,
            is_superuser=True,
            tier="premium",
        ))
        await db.commit()
        print(f"Superuser created — username: {username}  password: {password}")
        print("Change this password after your first login.")


if __name__ == "__main__":
    args = sys.argv[1:]
    asyncio.run(main(
        args[0] if args else "admin",
        args[1] if len(args) > 1 else "admin@football.watch",
        args[2] if len(args) > 2 else "ChangeMe123!",
    ))

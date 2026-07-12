"""
Run this to update stream URLs directly in the database.
Usage: python update_stream.py
"""
import asyncio
from database import init_db, AsyncSessionLocal
from models import Stream
from sqlalchemy import select

async def main():
    await init_db()
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Stream).where(Stream.match_id == 1))
        old = result.scalars().all()
        for s in old:
            await db.delete(s)

        new_stream = Stream(
            match_id=1,
            league_code="WC",
            label="TV1 Live",
            stream_url="https://rtmklik.rtm.gov.my/live/tv/tv1",
            stream_type="embed",
            language="Malay",
            is_active=True,
        )
        db.add(new_stream)
        await db.commit()
        print("Stream updated to RTM embed link")

if __name__ == "__main__":
    asyncio.run(main())

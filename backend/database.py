from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import settings

engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Columns added to already-existing tables after the first release.
# create_all() only ever creates MISSING TABLES — it will not alter a table that
# already exists — so new columns on `users` have to be added by hand or the
# running DB silently keeps the old shape.
_ADDED_COLUMNS: dict[str, dict[str, str]] = {
    "users": {
        "is_superuser": "BOOLEAN NOT NULL DEFAULT 0",
        "tier": "VARCHAR(20) NOT NULL DEFAULT 'free'",
    },
}


def _apply_column_migrations(conn) -> None:
    """Add any missing columns to existing tables. Safe to run on every boot."""
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names())

    for table, columns in _ADDED_COLUMNS.items():
        if table not in existing_tables:
            continue                      # create_all built it fresh, already correct
        present = {c["name"] for c in inspector.get_columns(table)}
        for name, ddl in columns.items():
            if name not in present:
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")
                print(f"[db] migrated: added {table}.{name}", flush=True)


async def init_db():
    # create_all only builds tables registered on Base.metadata, and a table is
    # registered when its module is imported. Import models here so init_db()
    # always sees the full schema — without this, calling it from a script that
    # hasn't imported models creates a silently incomplete database.
    import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_apply_column_migrations)

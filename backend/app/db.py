"""MongoDB connection (Motor) with a transparent in-memory fallback for demo mode."""

import logging
from typing import Any

from app.config import Settings
from app.seed_data import FAQS, build_orders

logger = logging.getLogger("agentdesk.db")


async def connect_mongo(settings: Settings) -> tuple[Any, str]:
    """Return (database handle, human-readable kind)."""
    if settings.mongodb_uri:
        from motor.motor_asyncio import AsyncIOMotorClient

        client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=4000)
        await client.admin.command("ping")
        logger.info("Connected to MongoDB")
        return client[settings.mongodb_db], "mongodb"

    from mongomock_motor import AsyncMongoMockClient

    logger.info("MONGODB_URI not set - using in-memory mongomock")
    return AsyncMongoMockClient()[settings.mongodb_db], "in-memory (mongomock)"


async def ensure_indexes(db: Any) -> None:
    await db.orders.create_index("order_id", unique=True)
    await db.faqs.create_index("id", unique=True)
    await db.tickets.create_index("ticket_id", unique=True)
    await db.conversations.create_index("session_id", unique=True)
    await db.messages.create_index([("session_id", 1), ("created_at", 1)])
    await db.messages.create_index("role")


async def seed(db: Any) -> None:
    """Idempotent: only inserts when a collection is empty."""
    if await db.orders.count_documents({}) == 0:
        await db.orders.insert_many(build_orders())
    if await db.faqs.count_documents({}) == 0:
        await db.faqs.insert_many([dict(f) for f in FAQS])


async def close_mongo(db: Any) -> None:
    try:
        db.client.close()
    except Exception:  # pragma: no cover - best effort on shutdown
        pass

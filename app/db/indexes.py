import logging

from app.db.session import db

logger = logging.getLogger(__name__)


async def ensure_indexes() -> None:
    """
    Create MongoDB indexes needed by the app.

    Note: the Atlas Search vector index ("vector_index") used by
    MongoDBVectorStore is a separate Atlas Search construct, not creatable
    via create_index() — it's assumed to already exist and is left untouched.
    """
    await db.chunks.create_index("parent_doc_id")
    await db.documents.create_index([("created_at", -1)])
    await db.llm_metrics.create_index([("timestamp", -1)])
    await db.rate_limits.create_index("date", unique=True)
    logger.info("MongoDB indexes ensured")

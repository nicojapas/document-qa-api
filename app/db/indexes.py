import logging

from app.db.session import db

logger = logging.getLogger(__name__)


async def ensure_indexes() -> None:
    """
    Create MongoDB indexes needed by the app. Best-effort: an index failing
    to build (e.g. pre-existing data violating a constraint) shouldn't take
    the whole app down, since these are performance optimizations, not
    correctness requirements.

    Note: the Atlas Search vector index ("vector_index") used by
    MongoDBVectorStore is a separate Atlas Search construct, not creatable
    via create_index() — it's assumed to already exist and is left untouched.
    """
    index_specs = [
        (db.chunks, "parent_doc_id", {}),
        (db.documents, [("created_at", -1)], {}),
        (db.llm_metrics, [("timestamp", -1)], {}),
        # Not unique: pre-existing rows may already have duplicate dates from
        # before this index existed, which would fail a unique index build.
        (db.rate_limits, "date", {}),
    ]

    for collection, keys, options in index_specs:
        try:
            await collection.create_index(keys, **options)
        except Exception:
            logger.exception(f"Failed to create index on {collection.name}: {keys!r}")

    logger.info("MongoDB indexes ensured")

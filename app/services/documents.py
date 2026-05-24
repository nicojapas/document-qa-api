import logging
from datetime import datetime

from bson import ObjectId

from app.core.config import settings
from app.db.session import db
from app.schemas.document import DocumentInDB, DocumentStatus
from app.services.embeddings import EmbeddingService
from app.services.vector_store import get_vector_store
from app.utils.text_splitter import split_and_process_text

logger = logging.getLogger(__name__)


class DocumentService:
    @staticmethod
    async def list_documents() -> list[DocumentInDB]:
        """Retrieve all documents from the database, sorted by creation date (newest first)."""
        cursor = db.documents.find().sort("created_at", -1)
        documents = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            documents.append(DocumentInDB(**doc))
        return documents

    @staticmethod
    async def create_document(filename: str, content_type: str, size: int) -> DocumentInDB:
        doc = DocumentInDB(
            filename=filename,
            content_type=content_type,
            size=size,
            status="processing",
            created_at=datetime.now(),
            id=None
        )
        # Insert into MongoDB
        result = await db.documents.insert_one(doc.model_dump())

        # Return the created doc with its new _id
        doc.id = str(result.inserted_id)

        return doc

    @staticmethod
    async def update_status(doc_id: str, status: DocumentStatus) -> None:
        """Update the status of a document."""
        await db.documents.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {"status": status.value}}
        )

    @staticmethod
    async def create_chunks(raw_text: str, parent_id: str):
        chunks = split_and_process_text(raw_text)

        # Limit chunks to prevent excessive embedding API costs
        original_count = len(chunks)
        if original_count > settings.MAX_CHUNKS_PER_DOCUMENT:
            chunks = chunks[:settings.MAX_CHUNKS_PER_DOCUMENT]
            logger.warning(
                f"Document {parent_id} truncated: {original_count} chunks -> {len(chunks)} chunks "
                f"(limit: {settings.MAX_CHUNKS_PER_DOCUMENT})"
            )

        # Generate all embeddings in efficient batches
        vectors = await EmbeddingService.generate_embeddings(chunks)

        # Store chunks using the configured vector store
        vector_store = get_vector_store()
        await vector_store.add_documents(chunks, vectors, parent_id)

import logging
from datetime import datetime

from app.core.config import settings
from app.db.session import db
from app.schemas.document import DocumentInDB
from app.services.embeddings import EmbeddingService
from app.utils.text_splitter import split_and_process_text

logger = logging.getLogger(__name__)


class DocumentService:
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

        chunk_documents = [
            {
                "parent_doc_id": parent_id,
                "index": index,
                "text": text,
                "embedding": vectors[index],
                "create_at": datetime.now()
            }
            for index, text in enumerate(chunks)
        ]

        if chunk_documents:
            await db.chunks.insert_many(chunk_documents)

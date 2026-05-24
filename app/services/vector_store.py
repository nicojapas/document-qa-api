from abc import ABC, abstractmethod
import logging
from pathlib import Path

import faiss
import numpy as np

from app.core.config import settings
from app.db.session import db

logger = logging.getLogger(__name__)


class VectorStore(ABC):
    """Abstract base class for vector store implementations."""

    @abstractmethod
    async def add_documents(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        parent_doc_id: str
    ) -> None:
        """Store document chunks with their embeddings."""
        pass

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        doc_id: str,
        top_k: int = 3
    ) -> list[str]:
        """Search for similar chunks and return their text."""
        pass

    @abstractmethod
    async def delete_document(self, doc_id: str) -> None:
        """Delete all chunks for a document."""
        pass


class MongoDBVectorStore(VectorStore):
    """
    Vector store using MongoDB Atlas Vector Search.

    Requires a vector search index named "vector_index" on the chunks collection
    with the "embedding" field configured for vector search.
    """

    async def add_documents(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        parent_doc_id: str
    ) -> None:
        from datetime import datetime

        chunk_documents = [
            {
                "parent_doc_id": parent_doc_id,
                "index": index,
                "text": text,
                "embedding": embeddings[index],
                "created_at": datetime.now()
            }
            for index, text in enumerate(texts)
        ]

        if chunk_documents:
            await db.chunks.insert_many(chunk_documents)
            logger.info(f"Stored {len(chunk_documents)} chunks in MongoDB for doc {parent_doc_id}")

    async def search(
        self,
        query_embedding: list[float],
        doc_id: str,
        top_k: int = 3
    ) -> list[str]:
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": 50,
                    "limit": top_k,
                    "filter": {"parent_doc_id": doc_id}
                }
            }
        ]
        cursor = db.chunks.aggregate(pipeline)
        results = await cursor.to_list(length=top_k)
        return [res["text"] for res in results]

    async def delete_document(self, doc_id: str) -> None:
        result = await db.chunks.delete_many({"parent_doc_id": doc_id})
        logger.info(f"Deleted {result.deleted_count} chunks for doc {doc_id}")


class FAISSVectorStore(VectorStore):
    """
    Vector store using FAISS for local/lightweight deployments.

    Stores vectors in a FAISS index (in-memory with optional file persistence)
    while keeping chunk metadata in MongoDB.

    How it works:
    - FAISS only stores vectors and returns integer IDs
    - We store chunk text/metadata in MongoDB with a "faiss_id" field
    - On search, FAISS returns IDs, we look up the text in MongoDB
    """

    _index: faiss.IndexFlatIP | None = None  # Inner product (cosine on normalized vectors)
    _dimension: int | None = None
    _index_path: Path = Path("data/faiss_index.bin")

    @classmethod
    def _ensure_index(cls, dimension: int) -> faiss.IndexFlatIP:
        """Get or create the FAISS index."""
        if cls._index is None:
            cls._dimension = dimension
            # Try to load existing index
            if cls._index_path.exists():
                try:
                    cls._index = faiss.read_index(str(cls._index_path))
                    logger.info(f"Loaded FAISS index with {cls._index.ntotal} vectors")
                except Exception as e:
                    logger.warning(f"Failed to load FAISS index: {e}")
                    cls._index = faiss.IndexFlatIP(dimension)
            else:
                cls._index = faiss.IndexFlatIP(dimension)
                cls._index_path.parent.mkdir(parents=True, exist_ok=True)
        return cls._index

    @classmethod
    def _save_index(cls) -> None:
        """Persist the index to disk."""
        if cls._index is not None:
            cls._index_path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(cls._index, str(cls._index_path))
            logger.info(f"Saved FAISS index with {cls._index.ntotal} vectors")

    async def add_documents(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        parent_doc_id: str
    ) -> None:
        from datetime import datetime

        if not embeddings:
            return

        dimension = len(embeddings[0])
        index = self._ensure_index(dimension)

        # Get starting ID for this batch
        start_id = index.ntotal

        # Normalize and add vectors to FAISS
        vectors = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(vectors)  # Normalize for cosine similarity
        index.add(vectors)

        # Store metadata in MongoDB with FAISS IDs
        chunk_documents = [
            {
                "parent_doc_id": parent_doc_id,
                "index": i,
                "text": text,
                "faiss_id": start_id + i,
                "created_at": datetime.now()
            }
            for i, text in enumerate(texts)
        ]

        if chunk_documents:
            await db.chunks.insert_many(chunk_documents)
            self._save_index()
            logger.info(f"Stored {len(chunk_documents)} chunks in FAISS for doc {parent_doc_id}")

    async def search(
        self,
        query_embedding: list[float],
        doc_id: str,
        top_k: int = 3
    ) -> list[str]:
        if self._index is None or self._index.ntotal == 0:
            logger.warning("FAISS index is empty")
            return []

        # Get all FAISS IDs for this document
        cursor = db.chunks.find(
            {"parent_doc_id": doc_id},
            {"faiss_id": 1, "text": 1}
        )
        doc_chunks = {doc["faiss_id"]: doc["text"] async for doc in cursor}

        if not doc_chunks:
            return []

        # Normalize query vector
        query = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query)

        # Search more candidates than needed since we filter by doc_id
        search_k = min(self._index.ntotal, top_k * 10)
        distances, indices = self._index.search(query, search_k)

        # Filter results to only include chunks from the requested document
        results = []
        for idx in indices[0]:
            if idx in doc_chunks:
                results.append(doc_chunks[idx])
                if len(results) >= top_k:
                    break

        return results

    async def delete_document(self, doc_id: str) -> None:
        # Note: FAISS IndexFlatIP doesn't support deletion
        # We remove from MongoDB; orphaned vectors remain in FAISS until rebuild
        result = await db.chunks.delete_many({"parent_doc_id": doc_id})
        logger.info(f"Deleted {result.deleted_count} chunks for doc {doc_id} (FAISS vectors orphaned)")


def get_vector_store() -> VectorStore:
    """Factory function to get the configured vector store."""
    store_type = settings.VECTOR_STORE.lower()

    if store_type == "faiss":
        return FAISSVectorStore()
    elif store_type == "mongodb":
        return MongoDBVectorStore()
    else:
        raise ValueError(f"Unknown vector store: {store_type}. Use 'faiss' or 'mongodb'.")


# Default instance for convenience
vector_store = get_vector_store()

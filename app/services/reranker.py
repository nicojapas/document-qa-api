import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class RerankerService:
    """
    Cross-encoder re-ranker, lazily loaded on first use.

    Lazy loading keeps app startup and /health fast, and avoids pulling the
    model into memory for deployments that never trigger a rerank (e.g. local
    dev runs that only exercise vector/hybrid retrieval).
    """

    _model = None

    @classmethod
    def _ensure_model(cls):
        if cls._model is None:
            from sentence_transformers import CrossEncoder

            logger.info(f"Loading cross-encoder reranker: {RERANKER_MODEL}")
            cls._model = CrossEncoder(RERANKER_MODEL)
        return cls._model

    @classmethod
    def rerank(
        cls, query: str, chunks: list["RetrievedChunk"], top_k: int
    ) -> list["RetrievedChunk"]:
        """
        Score each chunk against the query with the cross-encoder and return
        the top_k, sorted by rerank_score descending.

        This is a synchronous, CPU-bound call — callers must run it via
        asyncio.to_thread to avoid blocking the event loop.
        """
        if not chunks:
            return []

        model = cls._ensure_model()
        pairs = [(query, chunk.text) for chunk in chunks]
        scores = model.predict(pairs)

        for chunk, score in zip(chunks, scores):
            chunk.rerank_score = float(score)

        chunks.sort(key=lambda c: c.rerank_score, reverse=True)
        return chunks[:top_k]

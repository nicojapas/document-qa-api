import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Optional

from rank_bm25 import BM25Okapi

from app.db.session import db
from app.services.embeddings import EmbeddingService
from app.services.reranker import RerankerService
from app.services.vector_store import get_vector_store

logger = logging.getLogger(__name__)

RRF_K = 60


@dataclass
class RetrievedChunk:
    id: str
    doc_id: str
    index: int
    text: str
    vector_score: Optional[float] = None
    bm25_score: Optional[float] = None
    fused_score: Optional[float] = None
    rerank_score: Optional[float] = None


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _bm25_score_sync(
    query: str, docs: list[dict], doc_id: str, top_k: int
) -> list[RetrievedChunk]:
    corpus = [_tokenize(d["text"]) for d in docs]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(_tokenize(query))

    ranked_indices = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)[:top_k]

    return [
        RetrievedChunk(
            id=str(docs[i]["_id"]),
            doc_id=doc_id,
            index=docs[i]["index"],
            text=docs[i]["text"],
            bm25_score=float(scores[i]),
        )
        for i in ranked_indices
    ]


async def bm25_search(query: str, doc_id: str, top_k: int) -> list[RetrievedChunk]:
    """BM25 keyword search over a document's chunks, computed on the fly."""
    cursor = db.chunks.find({"parent_doc_id": doc_id}, {"text": 1, "index": 1})
    docs = [d async for d in cursor]

    if not docs:
        return []

    # BM25Okapi construction + scoring is CPU-bound (pure Python); keep it off
    # the event loop. The Mongo fetch above stays on the loop since the async
    # driver isn't safe to share across threads.
    return await asyncio.to_thread(_bm25_score_sync, query, docs, doc_id, top_k)


def reciprocal_rank_fusion(
    ranked_lists: list[list[RetrievedChunk]], k: int = RRF_K
) -> list[RetrievedChunk]:
    """
    Fuse multiple ranked lists into one via Reciprocal Rank Fusion.

    RRF needs no score normalization between BM25 (unbounded, corpus-dependent)
    and vector similarity (bounded cosine/IP) — each list only contributes rank
    position. k=60 is the standard constant from Cormack et al.'s original RRF.
    """
    scores: dict[str, float] = {}
    by_id: dict[str, RetrievedChunk] = {}

    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked, start=1):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
            by_id[chunk.id] = chunk

    for chunk_id, fused_score in scores.items():
        by_id[chunk_id].fused_score = fused_score

    return sorted(by_id.values(), key=lambda c: c.fused_score, reverse=True)


async def retrieve(
    queries: list[str],
    doc_id: str,
    *,
    mode: str = "hybrid_rerank",
    candidate_k: int = 10,
    final_k: int = 5,
) -> list[RetrievedChunk]:
    """
    Retrieve the most relevant chunks for a document using one of three modes:

    - "vector": vector search only, one ranking per (expanded) query, deduped
      by max vector_score. This is the pre-hybrid baseline.
    - "hybrid": vector rankings (one per query) + one BM25 ranking, fused via
      Reciprocal Rank Fusion.
    - "hybrid_rerank": same as "hybrid", then a cross-encoder re-ranks a wider
      candidate pool before truncating to final_k. Used by the live API.
    """
    vector_store = get_vector_store()

    ranked_lists: list[list[RetrievedChunk]] = []
    for q in queries:
        query_vector = await EmbeddingService.generate_embeddings([q], is_query=True)
        ranked_lists.append(await vector_store.search(query_vector, doc_id, top_k=candidate_k))

    if mode == "vector":
        best: dict[str, RetrievedChunk] = {}
        for ranked in ranked_lists:
            for chunk in ranked:
                current = best.get(chunk.id)
                if current is None or (chunk.vector_score or 0) > (current.vector_score or 0):
                    best[chunk.id] = chunk
        return sorted(best.values(), key=lambda c: c.vector_score or 0, reverse=True)[:final_k]

    # BM25 uses only the original literal question, not the LLM-paraphrased
    # variants — keyword overlap is most meaningful against what the user
    # actually typed.
    bm25_results = await bm25_search(queries[0], doc_id, candidate_k)
    fused = reciprocal_rank_fusion(ranked_lists + [bm25_results])

    if mode == "hybrid":
        return fused[:final_k]

    if mode == "hybrid_rerank":
        pool = fused[: max(final_k * 4, 20)]
        return await RerankerService.rerank(queries[0], pool, final_k)

    raise ValueError(f"Unknown retrieval mode: {mode!r}")

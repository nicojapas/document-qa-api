import logging
from typing import TYPE_CHECKING

import httpx

from app.core.config import settings

if TYPE_CHECKING:
    from app.services.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)

VOYAGE_RERANK_URL = "https://api.voyageai.com/v1/rerank"
RERANKER_MODEL = "rerank-2.5"


class RerankerService:
    """
    Cross-encoder re-ranking via the hosted Voyage AI rerank API.

    Runs as an HTTP call rather than in-process: loading sentence-transformers
    + torch locally was pushing the Render instance past its memory limit and
    triggering OOM restarts.
    """

    @classmethod
    async def rerank(
        cls, query: str, chunks: list["RetrievedChunk"], top_k: int
    ) -> list["RetrievedChunk"]:
        if not chunks:
            return []

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                VOYAGE_RERANK_URL,
                headers={"Authorization": f"Bearer {settings.VOYAGE_API_KEY}"},
                json={
                    "query": query,
                    "documents": [chunk.text for chunk in chunks],
                    "model": RERANKER_MODEL,
                    "top_k": top_k,
                },
            )
            response.raise_for_status()
            data = response.json()

        ranked: list["RetrievedChunk"] = []
        for result in data["data"]:
            chunk = chunks[result["index"]]
            chunk.rerank_score = result["relevance_score"]
            ranked.append(chunk)

        return ranked

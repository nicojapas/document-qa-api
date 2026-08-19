from typing import Optional
from pydantic import BaseModel


class QuestionRequest(BaseModel):
    document_id: str
    question: str
    model: Optional[str] = None


class SourceChunk(BaseModel):
    id: str
    doc_id: str
    index: int
    text: str
    vector_score: Optional[float] = None
    bm25_score: Optional[float] = None
    fused_score: Optional[float] = None
    rerank_score: Optional[float] = None


class AnswerResponse(BaseModel):
    queries: list[str]
    answer: str
    sources: list[SourceChunk]
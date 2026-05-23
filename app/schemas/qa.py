from typing import Optional
from pydantic import BaseModel


class QuestionRequest(BaseModel):
    document_id: str
    question: str
    model: Optional[str] = None
    
class AnswerResponse(BaseModel):
    queries: list[str]
    answer: str
    sources: list[str]
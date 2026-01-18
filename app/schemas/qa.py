from pydantic import BaseModel


class QuestionRequest(BaseModel):
    document_id: str
    question: str
    
class AnswerResponse(BaseModel):
    queries: list[str]
    answer: str
    sources: list[str]
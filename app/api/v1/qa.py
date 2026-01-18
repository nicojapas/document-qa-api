from fastapi import APIRouter, status

from app.schemas.qa import AnswerResponse, QuestionRequest
from app.services.llm import LLMService
from app.services.qa import QAService


router = APIRouter()

@router.post("/", response_model=AnswerResponse, status_code=status.HTTP_200_OK)
async def ask(payload: QuestionRequest):
    """
    Ask a question to the LLM.
    """
    # 1. Expand the query into 4 variations (original + 3 new ones)
    queries = await QAService.expand_query(payload.question)

    # 2. Retrieve
    context = await QAService.get_relevant_context(queries, payload.document_id)

    if not context:
        return {"answer": "I couldn't find any relevant info in that PDF.", "sources": []}

    # 3. Generate
    answer = await LLMService.answer_question(payload.question, context)
    
    return {"queries": queries, "answer": answer, "sources": context}

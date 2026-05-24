from fastapi import APIRouter, Depends, Request, status

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.qa import AnswerResponse, QuestionRequest
from app.services.llm import LLMService
from app.services.qa import QAService


router = APIRouter()


@router.post("/", response_model=AnswerResponse, status_code=status.HTTP_200_OK)
@limiter.limit(settings.RATE_LIMIT_QUESTIONS_PER_HOUR)
async def ask(request: Request, payload: QuestionRequest, _: User = Depends(get_current_user)):
    """
    Ask a question to the LLM.

    Requires authentication via Bearer token.
    """
    # 1. Expand the query into 4 variations (original + 3 new ones)
    queries = await QAService.expand_query(payload.question)

    # 2. Retrieve
    context = await QAService.get_relevant_context(queries, payload.document_id)

    if not context:
        return {"queries": queries, "answer": "I couldn't find any relevant info in that PDF.", "sources": []}

    # 3. Generate
    answer = await LLMService.answer_question(payload.question, context, payload.model)

    return {"queries": queries, "answer": answer, "sources": context}
